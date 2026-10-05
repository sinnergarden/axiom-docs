"""HISTORICAL FIXED-DATE CONTROL: Nov1-Jan31 teaching orchestration.

This retained control is not the new 65-session sliding entry point. Use
axiom_research.build_stock_ml_fold_from_saved_inputs for the saved moving fold.
No second training backend is introduced here.

Inputs are caller-owned frozen Feature parents and public Data scope evidence.
Feature execution, supplier collection and account execution are absent. All
numeric label normalization uses Research's existing Core-backed public API.
"""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime
import gc
from hashlib import sha256
import json
import math
from pathlib import Path
import resource
import time


def content_ref(value):
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode()
    return 'sha256:' + sha256(encoded).hexdigest()


def file_ref(path):
    result = sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return 'sha256:' + result.hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def run_weekly_pilot(manifest_path, destination):
    from axiom_data import Data, QuerySpec, adjust_prices
    from axiom_research import (load_stock_ml_experiment, build_forward_labels,
                                normalize_forward_labels, load_feature_catalog)
    import lightgbm as lgb
    import numpy as np

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    spec = read_json(manifest_path)
    started = time.monotonic()
    phases, queries, completed = [], [], []
    protected = {}

    def save(name, value):
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        # The external monitor also counts fixed-config and failed-attempt files.
        payload = json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode() + b'\n'
        assert sum(p.stat().st_size for p in destination.rglob('*') if p.is_file()) + len(payload) < 700 * 1024**2
        with path.open('xb') as stream:
            stream.write(payload)

    @contextmanager
    def phase(name):
        begin = time.monotonic()
        (destination / 'phase.json').write_text(json.dumps({'stage': name, 'started_monotonic': begin}))
        yield
        elapsed = time.monotonic() - begin
        assert elapsed < 120 and time.monotonic() - started < 480
        phases.append({'stage': name, 'elapsed_seconds': elapsed,
                       'process_high_water_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})

    # Each invocation revalidates proofs. A parent proof is verified once here
    # and released; the resulting finite Feature rows are reused by both folds.
    with phase('verification.public_experiment'):
        baseline = load_stock_ml_experiment(spec['experiment_path']).to_dict()
        config = baseline['definition']['config']
    with phase('verification.scope'):
        scope = read_json(spec['scope_path'])
        assert file_ref(spec['scope_path']) == spec['scope_file_ref']
        assert scope['source_proof']['source'] in ('Data.plan_scope', 'axiom_data.Data.plan_scope')
        calendar = scope['result']['read_sessions']
        assert calendar == sorted(set(calendar))
        assert scope['result']['snapshot_id'] == config['snapshot'] == spec['snapshot']
        assert scope['result']['pit_policy'] == config['pit_policy']
    symbols = config['symbols']
    selected = config['feature_selection']
    catalog = load_feature_catalog()
    # Catalog closure is checked by its compiler; this is inclusive history.
    lookback = max(feature['lookback'] for feature in catalog.select(selected))
    parents, rows, date_parent = {}, {}, {}
    for name, item in spec['parents'].items():
        with phase('verification.parent.' + name):
            features = read_json(item['features_path'])
            assert file_ref(item['features_path']) == item['features_file_ref']
            assert features['feature_ref'] == content_ref({k:v for k,v in features.items() if k!='feature_ref'})
            assert features['selection'] == selected
            if name != 'old':
                proof_path = Path(item['inputs_path'])
                assert file_ref(proof_path) == item['inputs_file_ref']
                proof = read_json(proof_path)
                assert features['input_evidence_ref'] == content_ref(proof)
                del proof
            parents[name] = features
            for path in [Path(item['features_path']), Path(item['inputs_path'])]:
                protected[str(path)] = (path.stat().st_size, path.stat().st_mtime_ns, file_ref(path))
            dates = sorted({row['session'] for row in features['rows']})
            assert len(features['rows']) == len(dates) * len(symbols)
            for day in dates:
                assert day not in date_parent
                date_parent[day] = name
            for row in features['rows']:
                key = row['session'], row['security_id']
                assert key not in rows and row['security_id'] in symbols
                rows[key] = row
            gc.collect()
    train_dates = [day for day in calendar if '2023-11-01' <= day <= '2024-01-31']
    assert len(symbols) == 314 and len(selected) == 6 and len(train_dates) == 65
    assert all(day in date_parent for day in train_dates)
    parameters = baseline['definition']['parameters']
    assert parameters['num_threads'] == 1 and baseline['definition']['num_boost_round'] == 100
    data = Data(spec['data_root'])

    def labels(wanted, cutoff):
        allowed = tuple(day for day in calendar if train_dates[0] <= day <= cutoff[:10])
        query = QuerySpec('market_daily', ('open', 'close'), tuple(symbols), allowed,
                         config['pit_policy'], {day:cutoff for day in allowed}, purpose='label_outcomes')
        batches = []
        for q in (query, replace(query, domain='adjustment_factors', fields=('factor',))):
            begin = time.monotonic()
            batch = data.read(snapshot=spec['snapshot'], query=q)
            queries.append({'query':{'domain':q.domain, 'fields':list(q.fields),
                'symbols':list(q.symbols), 'sessions':list(q.sessions), 'pit_policy':q.pit_policy,
                'cutoff_by_session':dict(q.cutoff_by_session), 'purpose':q.purpose,
                'price_basis':q.price_basis}, 'elapsed_seconds':time.monotonic()-begin})
            batches.append(batch)
        adjusted = adjust_prices(*batches, fields=('open','close'), anchor_session=allowed[-1],
                                 decision_session=allowed[-1], factor_field='factor')
        return build_forward_labels(adjusted, calendar=calendar, feature_sessions=wanted)

    def normalized(raw, wanted, cutoff, folder):
        combined = {}
        for name, parent in parents.items():
            dates = [day for day in wanted if date_parent[day] == name]
            if not dates:
                continue
            projection = {k:v for k,v in raw.items() if k not in ('rows','label_ref')}
            projection.update(rows=[row for row in raw['rows'] if row['feature_session'] in dates],
                              parent_label_ref=raw['label_ref'], feature_parent_ref=parent['feature_ref'],
                              date_projection=dates)
            projection['label_ref'] = content_ref(projection)
            value = normalize_forward_labels(projection, features=parent, cutoff=cutoff)
            save(folder + '/' + name + '-normalized.json', value)
            for row in value['rows']:
                combined[row['feature_session'],row['security_id']] = row
            del value, projection
            gc.collect()
        assert len(combined) == len(wanted) * len(symbols)
        return combined

    windows = [('2024-02-05','2024-02-08','2024-02-02'),
               ('2024-02-19','2024-02-23','2024-02-08')]
    shared_prediction_dates = sorted({calendar[calendar.index(day)-1]
        for first,last,_ in windows for day in calendar if first <= day <= last})
    # This is a declared common post-OOS clock, never a training clock. Sharing
    # one complete outcome proof avoids rereading it separately for each fold.
    outcome_cutoff = calendar[calendar.index(shared_prediction_dates[-1])+5] + 'T20:30:00+08:00'
    with phase('shared.evaluation_labels'):
        raw_eval = labels(shared_prediction_dates, outcome_cutoff)
        save('shared/evaluation-raw.json', raw_eval)
    with phase('shared.evaluation_normalization'):
        all_eval_targets = normalized(raw_eval, shared_prediction_dates, outcome_cutoff, 'shared/evaluation')
    del raw_eval
    for first, last, fit in windows:
        oos = [day for day in calendar if first <= day <= last]
        prediction_dates = sorted({calendar[calendar.index(day)-1] for day in oos})
        assert prediction_dates[0] == fit and all(day in date_parent for day in prediction_dates)
        fit_cutoff = fit + 'T20:30:00+08:00'
        folder = first
        with phase(folder + '.training_labels'):
            raw_train = labels(train_dates, fit_cutoff)
            save(folder + '/training-raw.json', raw_train)
        with phase(folder + '.training_normalization'):
            targets = normalized(raw_train, train_dates, fit_cutoff, folder + '/training')
        with phase(folder + '.matrix'):
            keys = [(day,symbol) for day in train_dates for symbol in symbols
                    if targets[day,symbol]['valid']]
            assert all(targets[key]['end_session'] <= fit and
                       datetime.fromisoformat(targets[key]['label_available_at'].replace('Z','+00:00')) <=
                       datetime.fromisoformat(fit_cutoff) for key in keys)
            prediction_keys = [(day,symbol) for day in prediction_dates for symbol in symbols
                               if rows[day,symbol]['member'] is True and
                               all(rows[day,symbol]['validity']) and
                               all(type(v) in (int,float) and math.isfinite(v) for v in rows[day,symbol]['values'])]
            X = np.asarray([rows[key]['values'] for key in keys], dtype=np.float64)
            y = np.asarray([targets[key]['normalized_target'] for key in keys], dtype=np.float64)
            P = np.asarray([rows[key]['values'] for key in prediction_keys], dtype=np.float64)
            assert np.isfinite(X).all() and np.isfinite(y).all() and np.isfinite(P).all()
            save(folder + '/dataset.json', {'training_keys':keys, 'prediction_keys':prediction_keys,
                 'fit_cutoff':fit_cutoff, 'feature_parent_refs':{k:v['feature_ref'] for k,v in parents.items()},
                 'columns':parents['old']['ordered_features'], 'matrix_bytes':X.nbytes+y.nbytes+P.nbytes})
        with phase(folder + '.fit'):
            model = lgb.train(dict(parameters), lgb.Dataset(X,label=y,feature_name=parents['old']['ordered_features']),
                              num_boost_round=baseline['definition']['num_boost_round'])
        with phase(folder + '.predict'):
            scores = model.predict(P, num_threads=1)
            assert np.isfinite(scores).all()
        model.save_model(str(destination / folder / 'booster.txt'))
        save(folder + '/predictions.json', {'contract_version':'private_weekly_teaching_predictions_v1',
             'not_public_ModelRelease_or_SignalRun':True, 'fit_cutoff':fit_cutoff,
             'rows':[{'session':key[0],'security_id':key[1],'score':float(score)} for key,score in zip(prediction_keys,scores)]})
        eval_targets = {key:value for key,value in all_eval_targets.items() if key[0] in prediction_dates}
        completed.append({'oos_start':first,'oos_end':last,'oos_sessions':len(oos),
             'fit_cutoff':fit_cutoff,'outcome_cutoff':outcome_cutoff,
             'training_rows':len(keys),'last_mature_feature_session':max(key[0] for key in keys),
             'prediction_rows':len(prediction_keys),'evaluation_valid_rows':sum(v['valid'] for v in eval_targets.values()),
             'matrix_bytes':X.nbytes+y.nbytes+P.nbytes,'fit_calls':1,'predict_calls':1})
        del X,y,P,model,raw_train,targets,eval_targets
        gc.collect()
    assert len(queries) == 6
    assert all((Path(p).stat().st_size,Path(p).stat().st_mtime_ns,file_ref(p)) == value for p,value in protected.items())
    receipt = {'status':'PASS','contract_version':'private_weekly_teaching_receipt_v1',
       'fixed_training_dates_not_sliding_window':True,'training_start':'2023-11-01','training_end':'2024-01-31',
       'folds':completed,'phases':phases,'queries':queries,'elapsed_seconds':time.monotonic()-started,
       'lookback_inclusive_sessions':lookback,'previous_context_sessions':lookback-1,
       'data_read_calls':6,'supplier_calls':0,'feature_core_calls':0,'fit_calls':2,'predict_calls':2,
       'shared_post_oos_outcome_cutoff':outcome_cutoff,
       'old_parent_files_unchanged':True,'streaming_loader_proven':False,
       'limitations':['314 January IDs performance control; not complete later CSI300',
                      'private teaching folds; not formal rolling API or account returns']}
    save('weekly-acceptance.json',receipt)
    return receipt
