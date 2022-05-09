#!/usr/bin/env bash

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <basename>"
  exit 1
fi

BASENAME=$1

openssl ecparam -name secp256k1 -genkey -noout -out "$BASENAME.key"
openssl ec -in "$BASENAME.key" -pubout > "$BASENAME.pub"
