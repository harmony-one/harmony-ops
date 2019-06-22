for x in {20..22}; do for y in `printf '%.2d ' {0..23}`; do curl https://harmony.one/201906$x/$y > $x$y 2> /dev/null; done; done; find . -size 65c -delete
s=(????)
for i in ${!s[@]}; do echo -n ${s[i]} ''; join <(grep -v ' -' ${s[i]} | sort) <(sort ${s[i+1]} /dev/null) | awk '/^one/ {print $1, $7 - $4}' | sort -rnk2 | head -1; done; echo

