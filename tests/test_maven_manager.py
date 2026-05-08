import os
import tempfile
import shutil
import xml.etree.ElementTree as ET
import pytest
from src.maven_manager import MavenProjectManager


@pytest.fixture
def temp_dir():
    """创建一个临时目录用于测试，测试结束后自动清理。"""
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)


@pytest.fixture
def manager():
    """提供一个基础的MavenProjectManager实例。"""
    return MavenProjectManager(
        group_id="com.example",
        artifact_id="my-app",
        version="1.0-SNAPSHOT"
    )


class TestDirectoryStructure:
    def test_create_directory_structure_creates_all_dirs(self, temp_dir):
        manager = MavenProjectManager("com.test", "test-app")
        manager.create_directory_structure(temp_dir)
        
        assert os.path.isdir(os.path.join(temp_dir, "src", "main", "java"))
        assert os.path.isdir(os.path.join(temp_dir, "src", "main", "resources"))
        assert os.path.isdir(os.path.join(temp_dir, "src", "test", "java"))
        assert os.path.isdir(os.path.join(temp_dir, "src", "test", "resources"))

    def test_create_directory_structure_idempotent(self, temp_dir):
        """多次调用不应报错。"""
        manager = MavenProjectManager("com.test", "test-app")
        manager.create_directory_structure(temp_dir)
        manager.create_directory_structure(temp_dir)
        assert os.path.isdir(os.path.join(temp_dir, "src", "main", "java"))


class TestPomGeneration:
    def test_generate_pom_xml_basic_content(self, temp_dir, manager):
        pom_path = manager.generate_pom_xml(temp_dir)
        assert os.path.exists(pom_path)
        
        tree = ET.parse(pom_path)
        root = tree.getroot()
        
        # Define namespace map for parsing
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
        
        assert root.find("m:groupId", ns).text == "com.example"
        assert root.find("m:artifactId", ns).text == "my-app"
        assert root.find("m:version", ns).text == "1.0-SNAPSHOT"
        assert root.find("m:packaging", ns).text == "jar"

    def test_generate_pom_xml_with_properties(self, temp_dir, manager):
        manager.set_java_version("11")
        manager.set_property("project.build.sourceEncoding", "UTF-8")
        pom_path = manager.generate_pom_xml(temp_dir)
        
        tree = ET.parse(pom_path)
        root = tree.getroot()
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
        
        props = root.find("m:properties", ns)
        assert props.find("m:maven.compiler.source", ns).text == "11"
        assert props.find("m:maven.compiler.target", ns).text == "11"
        assert props.find("m:project.build.sourceEncoding", ns).text == "UTF-8"

    def test_generate_pom_xml_with_dependencies(self, temp_dir, manager):
        manager.add_dependency("junit", "junit", "4.12", scope="test")
        pom_path = manager.generate_pom_xml(temp_dir)
        
        tree = ET.parse(pom_path)
        root = tree.getroot()
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
        
        deps = root.find("m:dependencies", ns)
        assert deps is not None
        dep = deps.find("m:dependency", ns)
        assert dep.find("m:groupId", ns).text == "junit"
        assert dep.find("m:artifactId", ns).text == "junit"
        assert dep.find("m:version", ns).text == "4.12"
        assert dep.find("m:scope", ns).text == "test"

    def test_generate_pom_xml_with_plugins(self, temp_dir, manager):
        pom_path = manager.generate_pom_xml(temp_dir)
        tree = ET.parse(pom_path)
        root = tree.getroot()
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
        
        build = root.find("m:build", ns)
        plugins = build.find("m:plugins", ns)
        
        plugin_ids = [p.find("m:artifactId", ns).text for p in plugins.findall("m:plugin", ns)]
        assert "maven-compiler-plugin" in plugin_ids
        assert "maven-surefire-plugin" in plugin_ids

    def test_generate_pom_xml_with_modules(self, temp_dir, manager):
        manager.packaging = "pom"
        manager.add_module("module-a")
        manager.add_module("module-b")
        pom_path = manager.generate_pom_xml(temp_dir)
        
        tree = ET.parse(pom_path)
        root = tree.getroot()
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
        
        modules = root.find("m:modules", ns)
        assert modules is not None
        module_names = [m.text for m in modules.findall("m:module", ns)]
        assert "module-a" in module_names
        assert "module-b" in module_names

    def test_generate_pom_xml_with_parent(self, temp_dir, manager):
        manager.set_parent("com.example.parent", "parent-pom", "1.0.0")
        pom_path = manager.generate_pom_xml(temp_dir)
        
        tree = ET.parse(pom_path)
        root = tree.getroot()
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
        
        parent = root.find("m:parent", ns)
        assert parent.find("m:groupId", ns).text == "com.example.parent"
        assert parent.find("m:artifactId", ns).text == "parent-pom"
        assert parent.find("m:version", ns).text == "1.0.0"


class TestDependencyManagement:
    def test_add_dependency(self, manager):
        manager.add_dependency("org.springframework", "spring-core", "5.3.9")
        deps = manager.get_dependencies()
        assert len(deps) == 1
        assert deps[0]["groupId"] == "org.springframework"

    def test_add_duplicate_dependency(self, manager):
        manager.add_dependency("org.springframework", "spring-core", "5.3.9")
        manager.add_dependency("org.springframework", "spring-core", "5.3.9")
        deps = manager.get_dependencies()
        assert len(deps) == 1

    def test_remove_dependency_exists(self, manager):
        manager.add_dependency("junit", "junit", "4.12")
        result = manager.remove_dependency("junit", "junit")
        assert result is True
        assert len(manager.get_dependencies()) == 0

    def test_remove_dependency_not_exists(self, manager):
        result = manager.remove_dependency("non-exist", "non-exist")
        assert result is False


class TestConflictDetection:
    def test_detect_no_conflict(self):
        deps = [
            {"groupId": "a", "artifactId": "lib", "version": "1.0"},
            {"groupId": "b", "artifactId": "lib", "version": "1.0"}
        ]
        conflicts = MavenProjectManager.detect_dependency_conflicts(deps)
        assert len(conflicts) == 0

    def test_detect_simple_conflict(self):
        deps = [
            {"groupId": "com.google.guava", "artifactId": "guava", "version": "20.0"},
            {"groupId": "com.google.guava", "artifactId": "guava", "version": "30.0"}
        ]
        conflicts = MavenProjectManager.detect_dependency_conflicts(deps)
        assert len(conflicts) == 1
        assert conflicts[0]["key"] == "com.google.guava:guava"
        assert "20.0" in conflicts[0]["versions"]
        assert "30.0" in conflicts[0]["versions"]
        # Suggested should be the higher version
        assert conflicts[0]["suggested"] == "30.0"

    def test_detect_multiple_conflicts(self):
        deps = [
            {"groupId": "a", "artifactId": "lib", "version": "1.0"},
            {"groupId": "a", "artifactId": "lib", "version": "2.0"},
            {"groupId": "b", "artifactId": "lib", "version": "1.0"},
            {"groupId": "b", "artifactId": "lib", "version": "1.5"}
        ]
        conflicts = MavenProjectManager.detect_dependency_conflicts(deps)
        assert len(conflicts) == 2


class TestLifecycleManagement:
    def test_run_lifecycle_success(self, temp_dir, manager):
        # Generate pom first so it exists
        manager.generate_pom_xml(temp_dir)
        code, msg = MavenProjectManager.run_maven_lifecycle(temp_dir, "compile")
        assert code == 0
        assert "BUILD SUCCESS" in msg
        assert "compile" in msg

    def test_run_lifecycle_invalid_phase(self, temp_dir, manager):
        manager.generate_pom_xml(temp_dir)
        code, msg = MavenProjectManager.run_maven_lifecycle(temp_dir, "invalid-phase")
        assert code == 1
        assert "Error" in msg

    def test_run_lifecycle_missing_pom(self, temp_dir):
        # Do not generate pom.xml
        code, msg = MavenProjectManager.run_maven_lifecycle(temp_dir, "compile")
        assert code == 1
        assert "pom.xml not found" in msg