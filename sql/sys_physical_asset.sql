-- 用户实物资产表（房产、车辆、贵金属、收藏品等）
-- 与基金/现金资产完全独立，不参与金融资产汇总、资产配置与持仓快照
CREATE TABLE IF NOT EXISTS `sys_physical_asset` (
  `asset_id` char(32) NOT NULL,
  `user_id` char(32) NOT NULL,
  `category` varchar(32) NOT NULL COMMENT '预设类别 house/vehicle/precious_metal/collectible/other，或字典 PHYSICAL_ASSET_CATEGORY 的 key',
  `name` varchar(128) NOT NULL COMMENT '资产名称',
  `current_value` decimal(18,2) NOT NULL COMMENT '当前估值',
  `cost_value` decimal(18,2) NOT NULL DEFAULT 0 COMMENT '购入成本',
  `cover` varchar(800) DEFAULT NULL COMMENT '封面图 URL',
  `images` json DEFAULT NULL COMMENT '实拍图 URL 数组',
  `purchase_date` date DEFAULT NULL COMMENT '购入日期',
  `valuation_date` date DEFAULT NULL COMMENT '最近估值日期',
  `remark` varchar(255) DEFAULT NULL,
  `sort` int NOT NULL DEFAULT 0,
  `create_time` datetime(6) NOT NULL,
  `update_time` datetime(6) NOT NULL,
  PRIMARY KEY (`asset_id`),
  KEY `idx_physical_asset_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户实物资产';
