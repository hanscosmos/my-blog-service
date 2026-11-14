-- 用户现金/存款资产表（余额宝等货币基金、银行存款）
-- 仅新增本表，不影响现有 sys_fund_holding 等表
CREATE TABLE IF NOT EXISTS `sys_cash_holding` (
  `holding_id` char(32) NOT NULL,
  `user_id` char(32) NOT NULL,
  `kind` varchar(16) NOT NULL COMMENT 'money_fund=货币基金/余额宝，deposit=银行存款',
  `name` varchar(128) NOT NULL,
  `fund_code` varchar(10) DEFAULT NULL COMMENT '货币基金代码，默认 000198',
  `balance` decimal(18,2) DEFAULT NULL COMMENT '当前余额（货币基金）',
  `principal` decimal(18,2) DEFAULT NULL COMMENT '投入本金',
  `annual_rate` decimal(8,4) DEFAULT NULL COMMENT '年化收益率(%)',
  `yesterday_pnl` decimal(18,2) DEFAULT NULL COMMENT '手填昨日收益，为空按行情预估',
  `start_date` date DEFAULT NULL COMMENT '存款起存日',
  `end_date` date DEFAULT NULL COMMENT '存款到期日',
  `interest_type` varchar(16) DEFAULT NULL COMMENT 'demand=活期，fixed=定期',
  `remark` varchar(255) DEFAULT NULL,
  `sort` int NOT NULL DEFAULT 0,
  `create_time` datetime(6) NOT NULL,
  `update_time` datetime(6) NOT NULL,
  PRIMARY KEY (`holding_id`),
  KEY `idx_cash_holding_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户现金存款资产';
