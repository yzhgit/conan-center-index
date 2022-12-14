import os
import shutil

from conans import ConanFile, tools, RunEnvironment, CMake


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake", "cmake_find_package_multi"

    def _build_with_cmake_find_package_multi(self):
        self.output.info("Building with cmake_find_package_multi")
        env_build = RunEnvironment(self)
        with tools.environment_append(env_build.vars):
            cmake = CMake(self, set_cmake_flags=True)
            if self.settings.os == "Macos":
                cmake.definitions['CMAKE_OSX_DEPLOYMENT_TARGET'] = '10.14'

            cmake.configure()
            cmake.build()

    def build(self):
        self._build_with_cmake_find_package_multi()

    def _test_with_cmake_find_package_multi(self):
        self.output.info("Testing CMake_find_package_multi")
        shutil.copy("qt.conf", "bin")
        self.run(os.path.join("bin", "test_package"), run_environment=True)

    def test(self):
        if not tools.cross_building(self, skip_x64_x86=True):
            self._test_with_cmake_find_package_multi()
