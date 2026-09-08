from codeforge.core.orchestration.orchestrator import CodeForgeOrchestrator
from codeforge.core.state import TaskPhase

def test_orchestrator_no_change(tmp_path):
    (tmp_path/'tests').mkdir(); (tmp_path/'tests'/'test_ok.py').write_text('def test_ok():\n    assert 1 == 1\n')
    state=CodeForgeOrchestrator(str(tmp_path)).run('inspect repository')
    assert state.phase in {TaskPhase.DONE,TaskPhase.FAILED}
    assert state.plan is not None

def test_orchestrator_patch(tmp_path):
    (tmp_path/'tests').mkdir(); (tmp_path/'app.py').write_text('VALUE = 1\n'); (tmp_path/'tests'/'test_app.py').write_text('from app import VALUE\ndef test_value():\n    assert VALUE == 2\n')
    patch={'file_path':'app.py','target_snippet':'VALUE = 1','replacement_snippet':'VALUE = 2'}
    state=CodeForgeOrchestrator(str(tmp_path)).run('change VALUE to 2',patch_suggestion=patch)
    assert state.test_results is not None
    assert any(c.file_path=='app.py' for c in state.changed_files)
