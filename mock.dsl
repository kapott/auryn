__DOMAIN__ = "byteherder.com"
__OUTPUT_DIR__ = "output/__DOMAIN__"

run "bash cert_transparency_check.sh __DOMAIN__"
  parsewith cert_transparency_check 
  output "__OUTPUT_DIR__/found_domains.txt" as $domain_list

map $domain_list 
  do "gobuster dir -u https://$domain_list -w paths.list -b 404,301 --no-color -q" 
  parsewith strip_ansi
  output "__OUTPUT_DIR__/found_https_paths.txt"
  as $found_https_paths

map $domain_list $found_https_paths
  do "echo https://$domain_list$found_https_paths"
  parsewith strip_ansi
  output "__OUTPUT_DIR__/found_permutations.txt"
  as $found_permutations