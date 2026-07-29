import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.variables import VariableStore
from core.condition_engine import ConditionEngine
from core.execution_log import ExecutionLog

def test_condition_engine():
    print("Testing ConditionEngine...")
    variables = VariableStore()
    variables.set("count", "5")
    variables.set("browser", "Chrome")
    
    engine = ConditionEngine(variables)
    
    # 1. Variable equality
    assert engine.evaluate("{count} == 5") is True
    assert engine.evaluate("{count} != 10") is True
    assert engine.evaluate("{count} > 3") is True
    assert engine.evaluate("{count} <= 5") is True
    
    # 2. String contains
    assert engine.evaluate("{browser} contains rome") is True
    assert engine.evaluate("{browser} not contains Firefox") is True
    
    # 3. Truthiness
    assert engine.evaluate("true") is True
    assert engine.evaluate("false") is False
    
    print("ConditionEngine OK!")

def test_execution_log():
    print("Testing ExecutionLog...")
    log = ExecutionLog(macro_name="TestMacro")
    
    log.add_entry(0, "move", "x=100, y=200", "SUCCESS", 0.05)
    log.add_entry(1, "run_app", "notepad.exe", "SUCCESS", 0.1)
    log.add_entry(2, "click", "left", "FAILED", 0.01, error="Element not found")
    
    log.save()
    assert os.path.exists(log.log_file)
    print("ExecutionLog OK! Saved to", log.log_file)

if __name__ == "__main__":
    test_condition_engine()
    test_execution_log()
    print("All Phase 2 tests passed!")
