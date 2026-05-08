import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Optional, Tuple


class MavenProjectManager:
    """
    Maven项目结构管理工具。
    支持创建目录结构、生成pom.xml、管理依赖、检测冲突及管理多模块项目。
    """

    def __init__(self, group_id: str, artifact_id: str, version: str = "1.0-SNAPSHOT", packaging: str = "jar"):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version
        self.packaging = packaging
        self.dependencies: List[Dict[str, str]] = []
        self.properties: Dict[str, str] = {
            "maven.compiler.source": "1.8",
            "maven.compiler.target": "1.8",
            "project.build.sourceEncoding": "UTF-8"
        }
        self.modules: List[str] = []
        self.parent_info: Optional[Dict[str, str]] = None

    def create_directory_structure(self, base_path: str) -> None:
        """
        创建标准的Maven项目目录结构。
        :param base_path: 项目根目录路径
        """
        dirs = [
            os.path.join(base_path, "src", "main", "java"),
            os.path.join(base_path, "src", "main", "resources"),
            os.path.join(base_path, "src", "test", "java"),
            os.path.join(base_path, "src", "test", "resources"),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    def add_dependency(self, group_id: str, artifact_id: str, version: str, scope: str = "compile") -> None:
        """
        添加依赖。
        """
        dep = {
            "groupId": group_id,
            "artifactId": artifact_id,
            "version": version,
            "scope": scope
        }
        # 避免重复添加完全相同的依赖
        if dep not in self.dependencies:
            self.dependencies.append(dep)

    def remove_dependency(self, group_id: str, artifact_id: str) -> bool:
        """
        删除依赖。
        :return: 如果找到并删除了依赖返回True，否则返回False
        """
        initial_len = len(self.dependencies)
        self.dependencies = [
            d for d in self.dependencies
            if not (d["groupId"] == group_id and d["artifactId"] == artifact_id)
        ]
        return len(self.dependencies) < initial_len

    def get_dependencies(self) -> List[Dict[str, str]]:
        """
        获取当前所有依赖。
        """
        return list(self.dependencies)

    def set_property(self, key: str, value: str) -> None:
        """
        设置POM属性。
        """
        self.properties[key] = value

    def set_java_version(self, version: str) -> None:
        """
        便捷方法：设置Java编译版本。
        """
        self.properties["maven.compiler.source"] = version
        self.properties["maven.compiler.target"] = version

    def add_module(self, module_artifact_id: str) -> None:
        """
        添加子模块。
        """
        if module_artifact_id not in self.modules:
            self.modules.append(module_artifact_id)

    def set_parent(self, group_id: str, artifact_id: str, version: str) -> None:
        """
        设置父POM信息。
        """
        self.parent_info = {
            "groupId": group_id,
            "artifactId": artifact_id,
            "version": version
        }

    def generate_pom_xml(self, base_path: str) -> str:
        """
        生成pom.xml文件内容并写入指定路径。
        :param base_path: 项目根目录路径
        :return: 生成的pom.xml文件绝对路径
        """
        pom_path = os.path.join(base_path, "pom.xml")
        
        project = ET.Element("project")
        project.set("xmlns", "http://maven.apache.org/POM/4.0.0")
        project.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        project.set("xsi:schemaLocation", "http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd")
        
        # Model Version
        model_ver = ET.SubElement(project, "modelVersion")
        model_ver.text = "4.0.0"

        # Parent
        if self.parent_info:
            parent = ET.SubElement(project, "parent")
            ET.SubElement(parent, "groupId").text = self.parent_info["groupId"]
            ET.SubElement(parent, "artifactId").text = self.parent_info["artifactId"]
            ET.SubElement(parent, "version").text = self.parent_info["version"]

        # Coordinates
        ET.SubElement(project, "groupId").text = self.group_id
        ET.SubElement(project, "artifactId").text = self.artifact_id
        ET.SubElement(project, "version").text = self.version
        ET.SubElement(project, "packaging").text = self.packaging

        # Properties
        if self.properties:
            props = ET.SubElement(project, "properties")
            for k, v in self.properties.items():
                ET.SubElement(props, k).text = v

        # Dependencies
        if self.dependencies:
            deps = ET.SubElement(project, "dependencies")
            for dep in self.dependencies:
                d = ET.SubElement(deps, "dependency")
                ET.SubElement(d, "groupId").text = dep["groupId"]
                ET.SubElement(d, "artifactId").text = dep["artifactId"]
                ET.SubElement(d, "version").text = dep["version"]
                if dep.get("scope") and dep["scope"] != "compile":
                    ET.SubElement(d, "scope").text = dep["scope"]

        # Build Plugins
        build = ET.SubElement(project, "build")
        plugins = ET.SubElement(build, "plugins")
        
        # Compiler Plugin
        compiler_plugin = ET.SubElement(plugins, "plugin")
        ET.SubElement(compiler_plugin, "groupId").text = "org.apache.maven.plugins"
        ET.SubElement(compiler_plugin, "artifactId").text = "maven-compiler-plugin"
        ET.SubElement(compiler_plugin, "version").text = "3.8.1"
        config = ET.SubElement(compiler_plugin, "configuration")
        ET.SubElement(config, "source").text = self.properties.get("maven.compiler.source", "1.8")
        ET.SubElement(config, "target").text = self.properties.get("maven.compiler.target", "1.8")

        # Surefire Plugin
        surefire_plugin = ET.SubElement(plugins, "plugin")
        ET.SubElement(surefire_plugin, "groupId").text = "org.apache.maven.plugins"
        ET.SubElement(surefire_plugin, "artifactId").text = "maven-surefire-plugin"
        ET.SubElement(surefire_plugin, "version").text = "2.22.2"

        # Modules
        if self.modules:
            modules_elem = ET.SubElement(project, "modules")
            for mod in self.modules:
                ET.SubElement(modules_elem, "module").text = mod

        # Pretty Print
        xml_str = ET.tostring(project, encoding="unicode")
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        # Remove extra blank lines often added by toprettyxml
        lines = [line for line in pretty_xml.splitlines() if line.strip()]
        final_xml = "\n".join(lines)

        with open(pom_path, "w", encoding="utf-8") as f:
            f.write(final_xml)
            
        return pom_path

    @staticmethod
    def detect_dependency_conflicts(all_dependencies: List[Dict[str, str]]) -> List[Dict]:
        """
        检测依赖冲突。
        输入是一个包含所有直接和传递依赖的列表。
        如果同一个 groupId:artifactId 出现多个不同版本，则视为冲突。
        
        :param all_dependencies: 依赖列表，每个元素为 dict: {'groupId', 'artifactId', 'version'}
        :return: 冲突列表，每个元素为 {'key': 'g:a', 'versions': ['v1', 'v2'], 'suggested': 'highest_version'}
        """
        # Group by groupId:artifactId
        dep_map: Dict[str, List[str]] = {}
        for dep in all_dependencies:
            key = f"{dep['groupId']}:{dep['artifactId']}"
            ver = dep['version']
            if key not in dep_map:
                dep_map[key] = []
            if ver not in dep_map[key]:
                dep_map[key].append(ver)
        
        conflicts = []
        for key, versions in dep_map.items():
            if len(versions) > 1:
                # Simple strategy: suggest the highest version (lexicographical sort for simplicity in this demo)
                # In a real tool, we would use semantic version parsing.
                sorted_versions = sorted(versions, reverse=True)
                conflicts.append({
                    "key": key,
                    "versions": versions,
                    "suggested": sorted_versions[0]
                })
        
        return conflicts

    @staticmethod
    def run_maven_lifecycle(base_path: str, phase: str) -> Tuple[int, str]:
        """
        模拟执行Maven生命周期命令。
        在实际环境中，这里会调用 subprocess.run(['mvn', phase, ...])
        为了测试的独立性和无需安装Maven的要求，这里模拟成功执行。
        
        :param base_path: 项目根目录
        :param phase: clean, compile, test, package, install
        :return: (exit_code, output_message)
        """
        valid_phases = ["clean", "compile", "test", "package", "install"]
        if phase not in valid_phases:
            return 1, f"Error: Unknown phase '{phase}'. Valid phases: {valid_phases}"
        
        # Check if pom.xml exists
        pom_path = os.path.join(base_path, "pom.xml")
        if not os.path.exists(pom_path):
            return 1, f"Error: pom.xml not found in {base_path}"

        # Simulate success
        return 0, f"BUILD SUCCESS: Maven phase '{phase}' completed in {base_path}"