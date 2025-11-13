#!/bin/bash
# Health check script for SoundCanvas services
# Usage: ./check_health.sh [environment]
# environment: local, staging, production

ENV=${1:-local}

if [ "$ENV" = "local" ]; then
  GATEWAY_URL="http://localhost:4000"
  CPP_CORE_URL="http://localhost:8080"
  AUDIO_PRODUCER_URL="http://localhost:5001"
elif [ "$ENV" = "staging" ]; then
  GATEWAY_URL="https://api-staging.soundcanvas.yourdomain.com"
  CPP_CORE_URL="http://cpp-core-staging:8080"
  AUDIO_PRODUCER_URL="http://audio-producer-staging:5001"
else
  GATEWAY_URL="https://api.soundcanvas.yourdomain.com"
  CPP_CORE_URL="http://cpp-core:8080"
  AUDIO_PRODUCER_URL="http://audio-producer:5001"
fi

echo "🔍 Checking SoundCanvas health for: $ENV"
echo "========================================="

# Check Gateway
echo -n "Gateway ($GATEWAY_URL): "
GATEWAY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/health")
if [ "$GATEWAY_STATUS" = "200" ]; then
  echo "✅ OK"
  curl -s "$GATEWAY_URL/health" | jq '.' 2>/dev/null || echo ""
else
  echo "❌ FAILED (HTTP $GATEWAY_STATUS)"
fi

echo ""

# Check GraphQL endpoint
echo -n "GraphQL ($GATEWAY_URL/graphql): "
GRAPHQL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "query { __typename }"}' \
  "$GATEWAY_URL/graphql")

if [ "$GRAPHQL_STATUS" = "200" ]; then
  echo "✅ OK"
else
  echo "❌ FAILED (HTTP $GRAPHQL_STATUS)"
fi

echo ""

# Only check internal services if not local
if [ "$ENV" != "local" ]; then
  echo -n "cpp-core: "
  # Ping test (services may not expose health endpoints)
  echo "⚠️  Internal service (not directly accessible)"
  
  echo -n "audio-producer: "
  echo "⚠️  Internal service (not directly accessible)"
fi

echo ""
echo "========================================="
echo "Health check complete for: $ENV"
