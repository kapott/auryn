#!/bin/bash

awk 'found_blank { print } NF==0 { found_blank=2 }' | grep "IN" | awk '{ print $5}' | 