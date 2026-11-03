


local strbyte, strlen, strsub, type = string.byte, string.len, string.sub, type

local function utf8charbytes(s, i)
	i = i or 1

	if type(s) ~= "string" then
		error("bad argument #1 to 'utf8charbytes' (string expected, got ".. type(s).. ")")
	end
	if type(i) ~= "number" then
		error("bad argument #2 to 'utf8charbytes' (number expected, got ".. type(i).. ")")
	end

	local c = strbyte(s, i)

	if c > 0 and c <= 127 then
		return 1

	elseif c >= 194 and c <= 223 then
		local c2 = strbyte(s, i + 1)

		if not c2 then
			error("UTF-8 string terminated early")
		end

		if c2 < 128 or c2 > 191 then
			error("Invalid UTF-8 character")
		end

		return 2

	elseif c >= 224 and c <= 239 then
		local c2 = strbyte(s, i + 1)
		local c3 = strbyte(s, i + 2)

		if not c2 or not c3 then
			error("UTF-8 string terminated early")
		end

		if c == 224 and (c2 < 160 or c2 > 191) then
			error("Invalid UTF-8 character")
		elseif c == 237 and (c2 < 128 or c2 > 159) then
			error("Invalid UTF-8 character")
		elseif c2 < 128 or c2 > 191 then
			error("Invalid UTF-8 character")
		end

		if c3 < 128 or c3 > 191 then
			error("Invalid UTF-8 character")
		end

		return 3

	elseif c >= 240 and c <= 244 then
		local c2 = strbyte(s, i + 1)
		local c3 = strbyte(s, i + 2)
		local c4 = strbyte(s, i + 3)

		if not c2 or not c3 or not c4 then
			error("UTF-8 string terminated early")
		end

		if c == 240 and (c2 < 144 or c2 > 191) then
			error("Invalid UTF-8 character")
		elseif c == 244 and (c2 < 128 or c2 > 143) then
			error("Invalid UTF-8 character")
		elseif c2 < 128 or c2 > 191 then
			error("Invalid UTF-8 character")
		end

		if c3 < 128 or c3 > 191 then
			error("Invalid UTF-8 character")
		end

		if c4 < 128 or c4 > 191 then
			error("Invalid UTF-8 character")
		end

		return 4

	else
		error("Invalid UTF-8 character")
	end
end

local function utf8len(s)
	if type(s) ~= "string" then
		error("bad argument #1 to 'utf8len' (string expected, got ".. type(s).. ")")
	end

	local pos = 1
	local bytes = strlen(s)
	local len = 0

	while pos <= bytes do
		len = len + 1
		pos = pos + utf8charbytes(s, pos)
	end

	return len
end

if not string.utf8len then
	string.utf8len = utf8len
end

local function utf8sub(s, i, j)
	j = j or -1

	if type(s) ~= "string" then
		error("bad argument #1 to 'utf8sub' (string expected, got ".. type(s).. ")")
	end
	if type(i) ~= "number" then
		error("bad argument #2 to 'utf8sub' (number expected, got ".. type(i).. ")")
	end
	if type(j) ~= "number" then
		error("bad argument #3 to 'utf8sub' (number expected, got ".. type(j).. ")")
	end

	local pos = 1
	local bytes = strlen(s)
	local len = 0

	local l = (i >= 0 and j >= 0) or utf8len(s)
	local startChar = (i >= 0) and i or l + i + 1
	local endChar   = (j >= 0) and j or l + j + 1

	if startChar > endChar then
		return ""
	end

	local startByte, endByte = 1, bytes

	while pos <= bytes do
		len = len + 1

		if len == startChar then
			startByte = pos
		end

		pos = pos + utf8charbytes(s, pos)

		if len == endChar then
			endByte = pos - 1
			break
		end
	end

	return strsub(s, startByte, endByte)
end

if not string.utf8sub then
	string.utf8sub = utf8sub
end

local function utf8replace(s, mapping)
	if type(s) ~= "string" then
		error("bad argument #1 to 'utf8replace' (string expected, got ".. type(s).. ")")
	end
	if type(mapping) ~= "table" then
		error("bad argument #2 to 'utf8replace' (table expected, got ".. type(mapping).. ")")
	end

	local pos = 1
	local bytes = strlen(s)
	local charbytes
	local newstr = ""

	while pos <= bytes do
		charbytes = utf8charbytes(s, pos)
		local c = strsub(s, pos, pos + charbytes - 1)

		newstr = newstr .. (mapping[c] or c)

		pos = pos + charbytes
	end

	return newstr
end

local function utf8upper(s)
	return utf8replace(s, utf8_lc_uc)
end

if not string.utf8upper and utf8_lc_uc then
	string.utf8upper = utf8upper
end

local function utf8lower(s)
	return utf8replace(s, utf8_uc_lc)
end

if not string.utf8lower and utf8_uc_lc then
	string.utf8lower = utf8lower
end

local function utf8reverse(s)
	if type(s) ~= "string" then
		error("bad argument #1 to 'utf8reverse' (string expected, got ".. type(s).. ")")
	end

	local bytes = strlen(s)
	local pos = bytes
	local charbytes
	local newstr = ""

	while pos > 0 do
		c = strbyte(s, pos)
		while c >= 128 and c <= 191 do
			pos = pos - 1
			c = strbyte(pos)
		end

		charbytes = utf8charbytes(s, pos)

		newstr = newstr .. strsub(s, pos, pos + charbytes - 1)

		pos = pos - 1
	end

	return newstr
end

if not string.utf8reverse then
	string.utf8reverse = utf8reverse
end