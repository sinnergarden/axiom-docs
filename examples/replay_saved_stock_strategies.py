"""Replay three independent accounts from the same saved stock predictions.

Requires axiom-engine 8d91726 and axiom-data b743b70 (or compatible descendants).
Supply an original bounded v8 request, its native Data delivery and all referenced
saved artifacts. This file contains no market data, local paths or credentials.
No supplier, Feature, fit or predict entrypoint is called. Daily predictions are
retained; the configured portfolio and exit checks run only at weekly rebalances.

Example:
    python replay_saved_stock_strategies.py --request inputs/request.json \
        --native-directory inputs/native --native-manifest-ref sha256:<actual> \
        --output results/three-strategies
"""
import argparse
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--native-directory',type=Path,required=True)
    parser.add_argument('--native-manifest-ref',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    from axiom_data import open_native_view
    from axiom_engine.core import stock_strategy_spec
    from axiom_engine.runtime import (BacktestRequest,StockNativeViewSource,StockMarketSpec,
        stock_portfolio_policy,admit_stock_market_inputs,bind_stock_prediction_inputs,
        StockResultSink,stock_run_id,run_stock_backtest,save_backtest_run)
    from axiom_engine.runtime.stock_stream_contracts import logical_ref,validate_manifest
    from axiom_engine.runtime.stock_rules import portfolio_support_ref

    assert 0<args.request.stat().st_size<=16*1024**2, 'Bounded request metadata required'
    base=validate_manifest(BacktestRequest(args.request.read_text()))
    assert base['contract_version']=='backtest_request_v8', 'Explicit equity facts/profile required'
    assert base['initial_account']=={'cash_minor':50000000,'positions':{}}, 'This example uses CNY500000'
    profile_path=Path(base['profile_input']['artifact']['manifest_uri'])
    assert 0<profile_path.stat().st_size<=16*1024**2, 'Bounded profile metadata required'
    profile=json.loads(profile_path.read_text())
    n=len(base['scope']['calendar']); u=len(base['scope']['execution_universe'])
    limits=dict(max_folds=64,max_prediction_rows=(n-1)*u,max_market_rows=(n+1)*u,
        max_input_bytes=4*1024**3,max_read_bytes=65536,max_block_bytes=4*1024**3,
        max_result_part_bytes=8*1024**2,max_result_buffer_bytes=64*1024**2,max_result_bytes=512*1024**2)
    variants=[('top5',stock_strategy_spec(top_k=5)),
        ('rank_buffer5_keep10',stock_strategy_spec(selection='rank_buffer',top_k=5,rank_buffer={'keep_rank':10})),
        ('top5_weekly_exit20_10',stock_strategy_spec(top_k=5,exit_overlay=dict(
            take_profit='0.20',stop_loss='0.10',cost_basis='fee_inclusive_ledger_cost_per_owned_share_v1',
            check='rebalance_sessions_only',cooldown_rebalance_sessions=1,reentry='after_flat_and_cooldown')))]
    requests=[]
    for name,spec in variants:
        wire=deepcopy(base); wire['account_id']=base['account_id']+'-'+name
        wire['portfolio_policy']=stock_portfolio_policy(strategy_spec=spec,
            universe_id='csi300',execution_universe=wire['scope']['execution_universe'],
            execution_rules=profile['stock_execution_rules'])
        wire['scope']['supported_universe_ref']=portfolio_support_ref(wire['portfolio_policy'],wire['scope']['execution_universe'])
        wire['request_ref']=logical_ref(wire,'request_ref')
        requests.append((name,BacktestRequest.from_dict(validate_manifest(wire))))
    assert len({r.to_dict()['prediction_input']['prediction_ref'] for _,r in requests})==1
    with ExitStack() as stack:
        handle=stack.enter_context(open_native_view(args.native_directory,manifest_sha256=args.native_manifest_ref,
            limits=dict(max_part_bytes=16*1024**2,max_rows_per_block=4096,
                max_saved_bytes=4*1024**3,max_working_bytes=4*1024**3)))
        source=stack.enter_context(StockNativeViewSource(native_views=[handle],max_active_bytes=limits['max_block_bytes']))
        market=stack.enter_context(admit_stock_market_inputs(StockMarketSpec.from_request(requests[0][1]),
            source=source,block_sessions=8,limits=limits,max_market_bytes=4*1024**3))
        for name,request in requests:
            root=args.output/name; root.mkdir(parents=True,exist_ok=False); tick=time.perf_counter()
            (root/'request.json').write_text(request.payload+'\n')
            with bind_stock_prediction_inputs(market,request,source=source,limits=limits,max_signal_bytes=1024**3) as admitted:
                sink=StockResultSink(root/'parts',run_id=stock_run_id(request.to_dict()))
                result=run_stock_backtest(request,source=admitted,sink=sink,block_sessions=8,limits=limits)
                save_backtest_run(result,root/'run.json')
            wire=result.to_dict()
            print(json.dumps(dict(strategy=name,run_id=wire['run_id'],status=wire['status'],
                seconds=time.perf_counter()-tick,path=str(root/'run.json')),ensure_ascii=False),flush=True)
            if wire['status']!='COMPLETE':
                raise RuntimeError('Account stopped; inspect the preserved result and its reason')


if __name__=='__main__': main()
