from typing import Dict, Any, Optional
from pathlib import Path
import json
import yaml
from datetime import datetime
from pydantic import BaseModel, Field
from jinja2 import Template

class PromptTemplate(BaseModel):
    """提示词模板模型"""
    name: str = Field(..., description="模板名称")
    version: str = Field(..., description="模板版本")
    description: str = Field(..., description="模板描述")
    template: str = Field(..., description="提示词模板")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    parameters: Dict[str, Any] = Field(default_factory=dict, description="模板参数定义")
    tags: list[str] = Field(default_factory=list, description="模板标签")
    category: str = Field(default="general", description="模板分类")

class PromptManager:
    """提示词管理器"""
    
    def __init__(self):
        """初始化提示词管理器"""
        self.templates: Dict[str, str] = {}
        
    def register_template(self, name: str, template: str) -> None:
        """
        注册提示词模板
        
        Args:
            name: 模板名称
            template: 模板内容
        """
        self.templates[name] = template
        
    def render_template(self, name: str, **kwargs) -> Optional[str]:
        """
        渲染提示词模板
        
        Args:
            name: 模板名称
            **kwargs: 模板参数
            
        Returns:
            Optional[str]: 渲染后的提示词，如果模板不存在则返回None
        """
        template = self.templates.get(name)
        if not template:
            return None
            
        try:
            jinja_template = Template(template)
            return jinja_template.render(**kwargs)
        except Exception as e:
            print(f"渲染模板时出错: {str(e)}")
            return None

    def __init__(self, templates_dir: Optional[str] = None):
        """
        初始化提示词管理器
        
        Args:
            templates_dir: 提示词模板目录路径，默认为 'prompts'
        """
        self.templates_dir = Path(templates_dir or "prompts")
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_templates()
        
    def _load_templates(self) -> None:
        """加载所有提示词模板"""
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载YAML格式的模板
        for yaml_file in self.templates_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    template_data = yaml.safe_load(f)
                    template = PromptTemplate(**template_data)
                    self.templates[template.name] = template
            except Exception as e:
                print(f"加载模板 {yaml_file} 失败: {str(e)}")
                
        # 加载JSON格式的模板
        for json_file in self.templates_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    template_data = json.load(f)
                    template = PromptTemplate(**template_data)
                    self.templates[template.name] = template
            except Exception as e:
                print(f"加载模板 {json_file} 失败: {str(e)}")
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        获取指定名称的提示词模板
        
        Args:
            name: 模板名称
            
        Returns:
            Optional[PromptTemplate]: 提示词模板，如果不存在则返回None
        """
        return self.templates.get(name)
    
    def add_template(self, template: PromptTemplate) -> None:
        """
        添加新的提示词模板
        
        Args:
            template: 提示词模板
        """
        template.updated_at = datetime.now()
        self.templates[template.name] = template
        
        # 保存到文件
        template_path = self.templates_dir / f"{template.name}.yaml"
        with open(template_path, "w", encoding="utf-8") as f:
            yaml.dump(template.dict(), f, allow_unicode=True)
    
    def update_template(self, name: str, **updates) -> Optional[PromptTemplate]:
        """
        更新现有的提示词模板
        
        Args:
            name: 模板名称
            **updates: 需要更新的字段
            
        Returns:
            Optional[PromptTemplate]: 更新后的模板，如果模板不存在则返回None
        """
        if name not in self.templates:
            return None
            
        template = self.templates[name]
        template_dict = template.dict()
        template_dict.update(updates)
        template_dict["updated_at"] = datetime.now()
        
        updated_template = PromptTemplate(**template_dict)
        self.templates[name] = updated_template
        
        # 保存到文件
        template_path = self.templates_dir / f"{name}.yaml"
        with open(template_path, "w", encoding="utf-8") as f:
            yaml.dump(updated_template.dict(), f, allow_unicode=True)
            
        return updated_template
    
    def delete_template(self, name: str) -> bool:
        """
        删除提示词模板
        
        Args:
            name: 模板名称
            
        Returns:
            bool: 是否删除成功
        """
        if name not in self.templates:
            return False
            
        template_path = self.templates_dir / f"{name}.yaml"
        if template_path.exists():
            template_path.unlink()
            
        del self.templates[name]
        return True
    
    def list_templates(self, category: Optional[str] = None, tag: Optional[str] = None) -> list[PromptTemplate]:
        """
        列出所有提示词模板
        
        Args:
            category: 可选的分类筛选
            tag: 可选的标签筛选
            
        Returns:
            list[PromptTemplate]: 符合条件的模板列表
        """
        templates = self.templates.values()
        
        if category:
            templates = [t for t in templates if t.category == category]
            
        if tag:
            templates = [t for t in templates if tag in t.tags]
            
        return sorted(templates, key=lambda x: x.updated_at, reverse=True) 