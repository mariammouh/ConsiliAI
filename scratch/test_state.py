import sys
import os

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, backend_path)

try:
    from main import _chat_state_response, _lab_downloads
    print("Successfully imported main functions")
    
    mock_state = {
        "idea": "test idea",
        "lab_exercises": [
            {
                "module_title": "Module 1",
                "lessons": [
                    {
                        "lab": {
                            "exercise_title": "Test Lab 1",
                            "instructions": "Test instructions"
                        },
                        "notebook_files": {
                            "starter": "/tmp/test.ipynb"
                        }
                    }
                ]
            }
        ]
    }
    
    res = _chat_state_response(mock_state)
    print("State response test result keys:", res.keys())
    print("Lab exercises in response:", res.get("lab_exercises"))
    print("Lab downloads in response:", res.get("lab_downloads"))
    
    # Test dict shape
    mock_state_dict = {
        "idea": "test idea 2",
        "lab_exercises": {
            "modules": [
                {
                    "module_title": "Module 2",
                    "lessons": [
                        {
                            "lab": {
                                "exercise_title": "Test Lab 2"
                            }
                        }
                    ]
                }
            ]
        }
    }
    res2 = _chat_state_response(mock_state_dict)
    print("Dict state response test result keys:", res2.keys())
    print("SUCCESS: backend state response works perfectly for both list and dict shapes!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
