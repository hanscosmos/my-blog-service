"""接口权限映射表

key  = 接口完整路径（request.path，含模块前缀）
value = 权限码（对应 sys_menu 中 type='3' 按钮节点的 code）

约定：
- 只登记「写操作」接口（增 / 删 / 改），未登记的路径默认放行；
- 读权限由菜单可见性（type='2' 页面节点）控制，不在此表登记；
- 用户操作自身数据的接口（个人资料 / 心情 / 个人事项等）不登记，任何登录用户都可访问；
- 接口路径变更时需同步修改本表。
"""

PERMISSION_PATH_MAP = {
    # ---------- 文章模块 ----------
    '/article/add': 'article:add',
    '/article/update': 'article:update',
    '/article/delete': 'article:delete',
    '/article/category/add': 'article:category:add',
    '/article/category/edit': 'article:category:update',
    '/article/category/delete': 'article:category:delete',
    '/article/tag/add': 'article:tag:add',
    '/article/tag/edit': 'article:tag:update',
    '/article/tag/delete': 'article:tag:delete',
    '/article/column/add': 'article:column:add',
    '/article/column/edit': 'article:column:update',
    '/article/column/delete': 'article:column:delete',
    # ---------- 权限模块 ----------
    '/authority/menu/add': 'authority:menu:add',
    '/authority/menu/edit': 'authority:menu:update',
    '/authority/menu/delete': 'authority:menu:delete',
    '/authority/role/add': 'authority:role:add',
    '/authority/role/edit': 'authority:role:update',
    '/authority/role/delete': 'authority:role:delete',
    '/authority/role/set/menu': 'authority:role:assign',
    # ---------- 资源模块 ----------
    '/resource/icon/add': 'resource:icon:add',
    '/resource/icon/edit': 'resource:icon:update',
    '/resource/icon/delete': 'resource:icon:delete',
    '/resource/icon/category/add': 'resource:icon-category:add',
    '/resource/icon/category/edit': 'resource:icon-category:update',
    '/resource/icon/category/delete': 'resource:icon-category:delete',
    '/resource/image/add': 'resource:image:add',
    '/resource/image/batch/add': 'resource:image:add',
    '/resource/image/edit': 'resource:image:update',
    '/resource/image/delete': 'resource:image:delete',
    '/resource/image/category/add': 'resource:image-category:add',
    '/resource/image/category/edit': 'resource:image-category:update',
    '/resource/image/category/delete': 'resource:image-category:delete',
    # ---------- 系统模块 ----------
    '/sys/dict/add': 'system:dict:add',
    '/sys/dict/edit': 'system:dict:update',
    '/sys/dict/delete': 'system:dict:delete',
    '/sys/dict/change/status': 'system:dict:status',
    '/sys/updateLog/add': 'system:log:add',
    '/sys/updateLog/edit': 'system:log:update',
    '/sys/updateLog/delete': 'system:log:delete',
    '/user/add': 'system:user:add',
    '/user/set/role': 'system:user:role',
    '/blogger/profile/update': 'system:blogger:update',
}
