#!/usr/bin/env bash

# ApexFlow Python Examples Runner Script
# Usage: ./run.sh [ecom|lead]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SDK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Resolve Python virtual environment interpreter
if [ -f "$PYTHON_SDK_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$PYTHON_SDK_DIR/venv/bin/python"
elif [ -f "$PYTHON_SDK_DIR/../apex-flow-backend/.venv/bin/python" ]; then
    PYTHON_BIN="$(cd "$PYTHON_SDK_DIR/../apex-flow-backend" && pwd)/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

print_usage() {
    echo "================================================="
    echo "🚀 ApexFlow Python Example Runner"
    echo "================================================="
    echo "Usage: ./run.sh <option>"
    echo ""
    echo "Available options:"
    echo "  ecom        | order       : E-Commerce Order Processing Pipeline (ecommerce_order_processing.py)"
    echo "  subworkflow | sub         : Parent & Child Sub-Workflow Lineage Demo (--subworkflow)"
    echo "  lead        | worker      : AI Lead Ingestion & Worker Example (worker_example.py)"
    echo "  large       | payload     : Large Payload Offloading Demo (large_payload_example.py)"
    echo "  enc         | encrypt     : Zero-Knowledge Payload Encryption Demo (encrypted_payload_example.py)"
    echo "  heartbeat   | hb          : Worker Heartbeat Monitoring Demo (worker_heartbeat_example.py)"
    echo ""
    echo "Examples:"
    echo "  ./run.sh ecom"
    echo "  ./run.sh large"
    echo "  ./run.sh enc"
    echo "  ./run.sh heartbeat"
    echo "================================================="
}

OPTION="${1:-}"
shift 2>/dev/null

case "$OPTION" in
    ecom|order)
        echo "Running E-Commerce Order Processing Example..."
        "$PYTHON_BIN" "$SCRIPT_DIR/ecommerce_order_processing.py" "$@"
        ;;
    subworkflow|sub-workflow|sub)
        echo "Running Parent & Child Sub-Workflow Lineage Example..."
        "$PYTHON_BIN" "$SCRIPT_DIR/ecommerce_order_processing.py" --subworkflow "$@"
        ;;
    lead|worker)
        echo "Running AI Lead Processing Example..."
        "$PYTHON_BIN" "$SCRIPT_DIR/worker_example.py" "$@"
        ;;
    large|payload)
        echo "Running Large Payload Offloading Example..."
        "$PYTHON_BIN" "$SCRIPT_DIR/large_payload_example.py" "$@"
        ;;
    enc|encrypt|crypto)
        echo "Running Zero-Knowledge Payload Encryption Example..."
        "$PYTHON_BIN" "$SCRIPT_DIR/encrypted_payload_example.py" "$@"
        ;;
    heartbeat|hb)
        echo "Running Worker Heartbeat Monitoring Example..."
        "$PYTHON_BIN" "$SCRIPT_DIR/worker_heartbeat_example.py" "$@"
        ;;
    -h|--help|help)
        print_usage
        ;;
    *)
        if [ -z "$OPTION" ]; then
            print_usage
        else
            echo "❌ Unknown option: '$OPTION'"
            echo ""
            print_usage
            exit 1
        fi
        ;;
esac

