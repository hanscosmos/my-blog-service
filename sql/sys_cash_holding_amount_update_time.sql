-- 为已存在的 sys_cash_holding 表补充「最近一次手动更新余额/本金的时间」
-- 新库直接执行 sql/sys_cash_holding.sql 即可，无需再执行本文件
ALTER TABLE `sys_cash_holding`
  ADD COLUMN `amount_update_time` datetime(6) DEFAULT NULL COMMENT '最近一次手动更新余额（货币基金）/本金（存款）的时间'
  AFTER `principal`;
