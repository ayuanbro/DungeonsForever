local ns = _G.DF_NS or {}

if (type(DF_Locale) ~= "function") or DF_Locale() ~= "enUS" then return end

-- 英文客户端：传承方案的标签与说明 / enUS: legacy plan labels and notes
local EN = {
    ["升级"] = "Leveling", ["冒险树按行推进，先满主力节点"] = "Advance the adventure tree row by row, maxing the core nodes first",
    ["专业"] = "Professions", ["专业树收益节点优先"] = "Prioritize the profession tree's payoff nodes",
    ["当前"] = "Current", ["按角色已投入显示"] = "Shows what this character has already invested",
}
for _, p in ipairs(ns.LegacyPlans or {}) do
    if type(p) == "table" then
        p.label = EN[p.label] or p.label
        p.note = EN[p.note] or p.note
    end
end
