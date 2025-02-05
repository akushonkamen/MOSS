import pytest
from datetime import datetime
from pathlib import Path
from src.services.llm.prompt_manager import PromptManager, PromptTemplate

@pytest.fixture
def temp_templates_dir(tmp_path):
    """创建临时模板目录"""
    templates_dir = tmp_path / "test_templates"
    templates_dir.mkdir()
    return str(templates_dir)

@pytest.fixture
def sample_template():
    """创建示例模板"""
    return PromptTemplate(
        name="test_template",
        version="1.0.0",
        description="Test template",
        template="Hello, {name}!",
        parameters={"name": {"type": "string", "description": "User name"}},
        tags=["test"],
        category="test"
    )

def test_init_prompt_manager(temp_templates_dir):
    """测试提示词管理器初始化"""
    manager = PromptManager(temp_templates_dir)
    assert isinstance(manager, PromptManager)
    assert Path(temp_templates_dir).exists()

def test_add_template(temp_templates_dir, sample_template):
    """测试添加模板"""
    manager = PromptManager(temp_templates_dir)
    manager.add_template(sample_template)
    
    # 验证内存中的模板
    assert "test_template" in manager.templates
    assert manager.templates["test_template"].name == "test_template"
    
    # 验证文件是否创建
    template_path = Path(temp_templates_dir) / "test_template.yaml"
    assert template_path.exists()

def test_get_template(temp_templates_dir, sample_template):
    """测试获取模板"""
    manager = PromptManager(temp_templates_dir)
    manager.add_template(sample_template)
    
    template = manager.get_template("test_template")
    assert template is not None
    assert template.name == "test_template"
    assert template.version == "1.0.0"

def test_update_template(temp_templates_dir, sample_template):
    """测试更新模板"""
    manager = PromptManager(temp_templates_dir)
    manager.add_template(sample_template)
    
    updated = manager.update_template(
        "test_template",
        description="Updated description",
        version="1.0.1"
    )
    
    assert updated is not None
    assert updated.description == "Updated description"
    assert updated.version == "1.0.1"
    
    # 验证文件是否更新
    template_path = Path(temp_templates_dir) / "test_template.yaml"
    assert template_path.exists()

def test_delete_template(temp_templates_dir, sample_template):
    """测试删除模板"""
    manager = PromptManager(temp_templates_dir)
    manager.add_template(sample_template)
    
    success = manager.delete_template("test_template")
    assert success
    
    # 验证内存中的模板是否删除
    assert "test_template" not in manager.templates
    
    # 验证文件是否删除
    template_path = Path(temp_templates_dir) / "test_template.yaml"
    assert not template_path.exists()

def test_render_template(temp_templates_dir, sample_template):
    """测试渲染模板"""
    manager = PromptManager(temp_templates_dir)
    manager.add_template(sample_template)
    
    result = manager.render_template("test_template", name="John")
    assert result == "Hello, John!"

def test_render_template_missing_params(temp_templates_dir, sample_template):
    """测试渲染模板时缺少参数"""
    manager = PromptManager(temp_templates_dir)
    manager.add_template(sample_template)
    
    result = manager.render_template("test_template")
    assert result is None

def test_list_templates(temp_templates_dir):
    """测试列出模板"""
    manager = PromptManager(temp_templates_dir)
    
    # 添加多个模板
    templates = [
        PromptTemplate(
            name=f"template_{i}",
            version="1.0.0",
            description=f"Template {i}",
            template="Test {i}",
            category="test" if i % 2 == 0 else "other",
            tags=["tag1"] if i % 2 == 0 else ["tag2"]
        ) for i in range(4)
    ]
    
    for template in templates:
        manager.add_template(template)
    
    # 测试无过滤
    all_templates = manager.list_templates()
    assert len(all_templates) == 4
    
    # 测试按分类过滤
    test_templates = manager.list_templates(category="test")
    assert len(test_templates) == 2
    assert all(t.category == "test" for t in test_templates)
    
    # 测试按标签过滤
    tag1_templates = manager.list_templates(tag="tag1")
    assert len(tag1_templates) == 2
    assert all("tag1" in t.tags for t in tag1_templates)

def test_load_templates(temp_templates_dir, sample_template):
    """测试加载模板"""
    # 创建第一个管理器并添加模板
    manager1 = PromptManager(temp_templates_dir)
    manager1.add_template(sample_template)
    
    # 创建新的管理器，验证是否能加载已存在的模板
    manager2 = PromptManager(temp_templates_dir)
    assert "test_template" in manager2.templates
    loaded_template = manager2.get_template("test_template")
    assert loaded_template is not None
    assert loaded_template.name == "test_template"
    assert loaded_template.version == "1.0.0" 