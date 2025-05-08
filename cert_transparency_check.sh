#!/usr/bin/env bash

# remove html tags
# sed 's/<[^>]*>//g'

crtsh(){
	local grep_domain
	grep_domain=$(echo $1 | sed "s/\%.*\%//g" | sed "s/\%//g")
	curl \
		-G \
		-m 9000 \
		-s \
		--data-urlencode "q=$1" \
		"https://crt.sh/" | \
		sed 's/<\/\?[^>]\+>//g' | \
		grep "$grep_domain" | \
		grep -v 'LIKE' | \
		grep -v 'crt.sh | %' | \
        sed 's/<[^>]*>/ /g' | \
        tr -s '[:space:]' '\n' | \
        sort -u | \
        grep -viE '^(\&nbsp;|after|at|issuer|not|before|after|serial|number|ID|CA|common|name|dns|public|crt\.sh|group|logged|by)$' | \
		grep -vE '^$'
}

mkdir -p "output/$1/ports/"
crtsh "%.$1"