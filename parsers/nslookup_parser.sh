#!/bin/bash

awk 'found_blank { print } NF==0 { found_blank=1 }' | grep "Address" | cut -d ' ' -f 2 | sort -u