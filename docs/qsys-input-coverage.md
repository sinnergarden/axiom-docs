# QSYS既有feature依赖覆盖与领域补采设计

状态：2026-10-11已批准最小设计；Source实现、合成验证和真实范围验收分别记录。本文件是设计与静态清单，未启动真实采集。

按领域一次聚合依赖；先复用Raw，再对残余字段发批量请求。

范围固定为历史CSI1800候选3,497代码、市场2014-11-03—2026-09-28的2,896交易日，事件请求2013-07-01—2026-09-28。先前2.7万—3.85万是基础单证券接口fallback估算，已被本首选批量计划替代。

## 九批

每批还必须携带ts_code和日期/事件键。日级三域采用(security_id,session)；财务保留report_type/end_date/ann_date/f_ann_date及可用context，不以update_flag推导公开修订顺序。

| 批次与所需字段 | 查询组织/首轮调用 | 既有Raw复用与薄映射 | PIT与供应商限制 |
|---|---|---|---|
| daily_basic：pe/pe_ttm,pb,ps/ps_ttm,total_mv/circ_mv,total/float/free_share,turnover_rate/turnover_rate_f,volume_ratio | 全市场trade_date，2,896次 | OHLCV/factor/amount复用；新增valuation_daily contract/profile，金额万元→CNY，股数万股→shares | cap6,000；当日15—17点更新是供应商一般规则，保守同日20:00假设；亏损PE为空，不能补0 |
| income_vip：新revenue,n_income,oper_cost；同一请求携带原core与事件键 | 沿用vip_month，公告月份窗口159次，report_type=1；非VIP才证券历史fallback | 旧income Raw已含total_revenue/n_income_attr_p及日期键；它们不等于新列。增加同域v3字段/状态映射，显式只重建financial_events | 原实际公告日/下一开盘假设、实际receipt保留；VIP历史成功但当前额度未probe |
| balancesheet_vip：新inventories,accounts_receiv；原core与事件键 | 公告月份159次 | 复用total_assets/total_liab/parent_equity Raw；只补两列；显式只重建balance_sheet_events。current_ratio已有独立供应商列，不为凑数量请求total_cur_assets/liab | 同上；金额CNY，period-end stock不能当YTD |
| fina_indicator_vip：新grossprofit_margin,current_ratio；原roe/roe_waa/debt_to_assets与事件键 | report period季度全市场52次（2013Q3—2026Q2） | 复用原ROE/负债率Raw；补两列、同域v3、只重建financial_indicator_events。roe_ttm不在实际闭包，不采 | percent与ratio分开；base cap100仅fallback。VIP数值cap未公开，不能自行虚构完整性证明 |
| moneyflow：net_mf_amount,buy_elg_amount,sell_elg_amount | 全市场trade_date，2,896次；残余才按证券 | 市场/日历/identity复用；新增money_flow_daily contract/profile，万元→CNY；net_inflow绑定原生net，big_inflow由Research做超大单买卖差 | cap6,000；历史起点2010；净流入不能用桶合计相减。保守同日收盘后假设，不冒充逐日公开时戳 |
| margin_detail：rzye,rzmre,rzche,rzrqye,rqyl,rqchl,rqmcl | 全市场trade_date，2,896次 | 原价格/流通市值分别复用；新增margin_daily contract/profile，货币CNY，证券数量单位明确 | cap6,000；上一日数据次日上午约08:30，深/北周五下周一；rqmcl股/份/手需证券类型绑定；非两融与缺数据分开 |
| stk_holdernumber：holder_num,ann_date,end_date | ts_code可省略，公告月/时间窗口批采159起；cap窗口二分，残余成本高时切证券历史；预算159—3,497 | top10 Raw已存在，绝不重拉；新增shareholder_count_events，保留完整公告事件，由Research选择可见前次/前两次 | cap3,000；文档2000积分200次/分钟；month date参数是公告日期，不是季度report_period |
| forecast_vip：type,ann_date,first_ann_date,end_date | 首选公告月窗口159次，覆盖对未来报告期的提前预告；base ann_date文档有市场示例，按实测成本选fallback | 无已采预告Raw；新增forecast_events，type保存原字符串，分数Research计算 | base cap3,500，20—21更新；首公告日期不能作为后来更正type的提前可用时刻；VIP当前权限未probe |
| index_classify + index_member_all：l1/l2/l3 IDs、ts_code,in_date,out_date,is_new | 2类taxonomy×3级catalog=6次；先分类整批显式Y/N，满cap下钻；约124—1,200次 | 原CSI成员Raw保留，行业是独立域；新增industry_membership_events，存原区间和taxonomy证据，不把成员指数分类当行业 | member cap2,000、默认Y会漏历史；只有区间日期，没有公开时刻；catalog src并不证明member每行taxonomy版本，out_date边界待明确 |

主预算：3×2,896 + 159 +159 +52 +159 +(159…3,497) +(124…1,200) = **9,500…13,914次**。加20%暂按11,400…16,700；如果可持续100次/分钟，纯请求约1.9—2.8小时。当前额度、归一化/显式重建及发布耗时未实测；整体时长不承诺，释放资源后小批校正。新增raw/canonical磁盘8—20GiB、预留30GiB仍为待测规划范围。

## Raw复用裁决

既有金融批采采用VIP公告月/报告季度路径，新的残余字段优先沿用该批量组织。历史成功不证明当前账户额度；正式启动先小批核验，禁止购买积分或改变账户权限。旧请求冻结core字段，并非默认全字段捕获。income已请求total_revenue/n_income_attr_p，balance已请求total_assets/total_liab/parent_equity，indicator已请求roe/roe_waa/debt_to_assets；这些列不能替代revenue/n_income/inventories/accounts_receiv等缺列。

先检查所选Raw的实际fields头及完整closure；已经保存的新列优先离线映射，取消对应补采selector。旧字段不单独重采；残余金融请求一次返回所需字段并集及原core，保留一致的供应商修订行，不拼接不同receipt成供应商从未返回的行。旧Raw、真实receipt和旧Snapshot不变。

## 正式代码的最小边界（本次未编码）

1. **Source适配**：只扩展现有endpoint请求、SourceProfile、units/date/identity/shape校验和领域contract；继续使用现有Raw-first/typed Parquet/bounded chunk/retry/checkpoint。保留旧默认request-fields与normalizer语义不变，新增显式输入field-set版本。provider_local现有select_source_rows按endpoint FIELDS校验，不能只把新endpoint塞给records_v1然后跳过范围校验。不动bulk/CLI/verification文件，不建新服务、registry或全局缓存。
2. **金融三域**：新contract/profile只在显式请求启用；Data.rebuild的domain_overrides，仅替换financial_events、balance_sheet_events、financial_indicator_events，输入所选旧Raw完整closure和新原生Raw，保留原observed_at；旧Raw新列明确missing status。市场/成员/现金流/top10/权益事实等其它域原样复用。普通update不能静默修改旧contract。
3. **Consumer层**：volume/VWAP导出缺口；QSYS的别名、单位、TTM/单季/公告前次、行业汇总/截面rank、资金流差值都归Research。Data存供应商事实，不计算策略feature。年度shift语义、pe→pe_ttm的legacy名称差异须显式审查，不把名称当native字段证明。
4. **验收**：小型合成验证单位、范围/分页cap、unknown/不适用、财务YTD/stock basis、late→early cutoff、同日修订、预告更正、行业历史变化、旧Raw回放及旧Snapshot不变。首次正式probe少量请求确认VIP/日期市场批采、cap与完整字段后再冻结计划；采集不在本次启动。

## 表达式、算子和数据覆盖分别裁决

388行是表达式/键清单，不是已实现数。字段轴213可绑定、56缺export、119缺采集；这三类不能当impl验收。

实现轴目前只确认与当前A01匹配的77个Alpha表达式；其余**81个Alpha表达式**涉及VWAP/BETA/RSQR/RESI/QTLU/QTLD/IMAX/IMIN/IMXD/CORR/CORD/VMA/VSTD/WVMA/VSUMP/VSUMN/VSUMD，另**230个custom/raw/规范化/配置键**待Research移植或别名/公式等价审查。不能把311叫311个全新算子。

Alpha表达式的18个算子依赖单列：Abs,Corr,Greater,IdxMax,IdxMin,Less,Log,Max,Mean,Min,Quantile,Rank,Ref,Resi,Rsquare,Slope,Std,Sum。这里是需求集合，**没有完成与Core现有算子的逐项实现盘点**，所以缺算子数仍未认证。跨截面rank、财务期间对齐、公告事件前次及行业聚合属于语义/组合层；按共用算子一次实现，不按feature建采集任务。后续组合启动前用冻结表达式closure做preflight，已impl、export、数据范围、单位、PIT和warmup均明确才进入重case。

官方依据：[daily_basic](https://tushare.pro/document/2?doc_id=32)、[income](https://tushare.pro/document/2?doc_id=33)、[balancesheet](https://tushare.pro/document/2?doc_id=36)、[fina_indicator](https://tushare.pro/document/2?doc_id=79)、[moneyflow](https://tushare.pro/document/2?doc_id=170)、[margin_detail](https://tushare.pro/document/2?doc_id=59)、[stk_holdernumber](https://tushare.pro/document/2?doc_id=166)、[forecast](https://tushare.pro/document/2?doc_id=45)、[index_member_all](https://tushare.pro/document/2?doc_id=335)。


## 静态清单证据

[完整feature依赖清单](qsys-feature-dependencies.csv)固定SysQ commit `852bcb73125f8781b7a80618b8188928ef4d38f2`与Qlib 0.9.7。13组182次登记去重180键；Alpha158 158、raw扩展22，semantic_all fallback合并360键；规范化另加15表达式得375，配置另加13键，合计388行。52个参考文件逐个Git blob SHA一致。registry_v2为样例，不作为全集。模型bundle选择清单未作为本清单来源。

表达式依赖使用源码AST与审查过的loader/raw别名；窗口hint不是精确warmup证明。当前A01 catalog仅作实现存在性对照，不代表运行验收。字段/impl状态是独立轴，未测逐证券日期完整性。
