#!/bin/bash
# Hugo 构建脚本（带 GitHub Token 支持）

set -a
source .env
set +a

hugo "$@"
