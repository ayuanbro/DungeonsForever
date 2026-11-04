local ns = _G.DF_NS or {}

local P = {
    {
        key = 'level',
        label = '升级',
        note = '冒险树按行推进，先满主力节点',
        seq = {
            { nid = 110301, rank = 5, tree = 2, row = 2, col = 1 },
            { nid = 110298, rank = 5, tree = 2, row = 2, col = 3 },
            { nid = 110296, rank = 3, tree = 2, row = 3, col = 1 },
            { nid = 110304, rank = 3, tree = 2, row = 3, col = 2 },
        },
    },
    {
        key = 'prof',
        label = '专业',
        note = '专业树收益节点优先',
        seq = {
            { nid = 110290, rank = 5, tree = 1, row = 2, col = 1 },
            { nid = 110286, rank = 2, tree = 1, row = 2, col = 2 },
            { nid = 110284, rank = 1, tree = 1, row = 2, col = 3 },
            { nid = 110291, rank = 5, tree = 1, row = 3, col = 1 },
            { nid = 110292, rank = 3, tree = 1, row = 3, col = 2 },
        },
    },
    {
        key = 'cur',
        label = '当前',
        note = '按角色已投入显示',
        seq = {},
    },
}

ns.LegacyPlans = P
