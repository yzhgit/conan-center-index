from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import build_jobs, check_min_cppstd, cross_building
from conan.tools.files import chdir, get, load, replace_in_file, rm, rmdir, save, export_conandata_patches, apply_conandata_patches
from conan.tools.microsoft import msvc_runtime_flag, is_msvc
from conan.tools.scm import Version
from conans import tools, RunEnvironment
from conans.model import Generator
import configparser
import glob
import itertools
import os
import textwrap

required_conan_version = ">=1.52.0"


class qt(Generator):
    @property
    def filename(self):
        return "qt.conf"

    @property
    def content(self):
        return """[Paths]
Prefix = %s
""" % self.conanfile.deps_cpp_info["qt"].rootpath.replace("\\", "/")


class QtConan(ConanFile):
    _submodules = ["qtsvg", "qtdeclarative", "qtactiveqt", "qtscript", "qtmultimedia", "qtxmlpatterns",
    "qtdoc", "qtlocation", "qtsensors", "qtconnectivity", "qtwayland",
    "qt3d", "qtimageformats", "qtgraphicaleffects", "qtquickcontrols", "qtserialbus", "qtserialport", "qtx11extras",
    "qtmacextras", "qtwinextras", "qtandroidextras", "qtwebsockets", "qtwebchannel", "qtwebengine", "qtwebview",
    "qtquickcontrols2", "qtpurchasing", "qtcharts", "qtdatavis3d", "qtvirtualkeyboard", "qtgamepad", "qtscxml",
    "qtspeech", "qtnetworkauth", "qtremoteobjects", "qtwebglplugin", "qtlottie", "qtquicktimeline", "qtquick3d"]

    name = "qt"
    description = "Qt is a cross-platform framework for graphical user interfaces."
    topics = ("ui", "framework")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.qt.io"
    license = "LGPL-3.0"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "opengl": ["no", "es2", "desktop", "dynamic"],
        "device": "ANY",
        "cross_compile": "ANY",
        "sysroot": "ANY",
        "multiconfiguration": [True, False]
    }

    default_options = {
        "shared": False,
        "opengl": "no",
        "device": None,
        "cross_compile": None,
        "sysroot": None,
        "multiconfiguration": False
    }

    no_copy_source = True
    short_paths = True
    generators = "pkg_config"

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def export(self):
        self.copy(f"qtmodules{self.version}.conf")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        if self._settings_build.os == "Windows" and is_msvc(self):
            self.build_requires("jom/1.1.3")

    def config_options(self):
        if self.settings.compiler == "apple-clang":
            if Version(self.settings.compiler.version) < "10.0":
                raise ConanInvalidConfiguration("Old versions of apple sdk are not supported by Qt (QTBUG-76777)")
        if self.settings.compiler in ["gcc", "clang"]:
            if Version(self.settings.compiler.version) < "5.0":
                raise ConanInvalidConfiguration("qt 5.15.X does not support GCC or clang before 5.0")
        if self.settings.os == "Windows":
            self.options.opengl = "dynamic"

    def configure(self):
        if self.options.multiconfiguration:
            del self.settings.build_type

        config = configparser.ConfigParser()
        config.read(os.path.join(self.recipe_folder, f"qtmodules{self.version}.conf"))
        submodules_tree = {}
        assert config.sections(), f"no qtmodules.conf file for version {self.version}"
        for s in config.sections():
            section = str(s)
            assert section.startswith("submodule ")
            assert section.count('"') == 2
            modulename = section[section.find('"') + 1: section.rfind('"')]
            status = str(config.get(section, "status"))
            if status not in ("obsolete", "ignore"):
                submodules_tree[modulename] = {"status": status,
                                "path": str(config.get(section, "path")), "depends": []}
                if config.has_option(section, "depends"):
                    submodules_tree[modulename]["depends"] = [str(i) for i in config.get(section, "depends").split()]

        for m in submodules_tree:
            assert m in ["qtbase", "qtqa", "qtrepotools", "qttranslations", "qttools"] or m in self._submodules, "module %s is not present in recipe options : (%s)" % (m, ",".join(self._submodules))


    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, "11")

        if self.settings.os == "Android" and self.options.get_safe("opengl", "no") == "desktop":
            raise ConanInvalidConfiguration("OpenGL desktop is not supported on Android. Consider using OpenGL es2")

        if self.settings.os != "Windows" and self.options.get_safe("opengl", "no") == "dynamic":
            raise ConanInvalidConfiguration("Dynamic OpenGL is supported only on Windows.")

        if "MT" in self.settings.get_safe("compiler.runtime", default="") and self.options.shared:
            raise ConanInvalidConfiguration("Qt cannot be built as shared library with static runtime")

        if self.settings.compiler == "apple-clang":
            if Version(self.settings.compiler.version) < "10.0":
                raise ConanInvalidConfiguration("Old versions of apple sdk are not supported by Qt (QTBUG-76777)")
        if self.settings.compiler in ["gcc", "clang"]:
            if Version(self.settings.compiler.version) < "5.0":
                raise ConanInvalidConfiguration("qt 5.15.X does not support GCC or clang before 5.0")

        if cross_building(self) and self.options.cross_compile == "None":
            raise ConanInvalidConfiguration("option cross_compile must be set for cross compilation "
                                            "cf https://doc.qt.io/qt-5/configure-options.html#cross-compilation-options")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True, destination="qt5")

        apply_conandata_patches(self)
        for f in ["renderer", os.path.join("renderer", "core"), os.path.join("renderer", "platform")]:
            replace_in_file(self, os.path.join(self.source_folder, "qt5", "qtwebengine", "src", "3rdparty", "chromium", "third_party", "blink", f, "BUILD.gn"),
                "  if (enable_precompiled_headers) {\n    if (is_win) {",
                "  if (enable_precompiled_headers) {\n    if (false) {"
            )
        replace_in_file(self, os.path.join(self.source_folder, "qt5", "qtbase", "configure.json"),
            "-ldbus-1d",
            "-ldbus-1"
        )
        open(os.path.join(self.source_folder, "qt5", "qtbase", "mkspecs", "features", "uikit", "bitcode.prf"), "w").close()

    def _make_program(self):
        if is_msvc(self):
            return "jom"
        elif self._settings_build.os == "Windows":
            return "mingw32-make"
        else:
            return "make"

    def _xplatform(self):
        if self.settings.os == "Linux":
            if self.settings.compiler == "gcc":
                return {"x86": "linux-g++-32",
                        "armv6": "linux-arm-gnueabi-g++",
                        "armv7": "linux-arm-gnueabi-g++",
                        "armv7hf": "linux-arm-gnueabi-g++",
                        "armv8": "linux-aarch64-gnu-g++"}.get(str(self.settings.arch), "linux-g++")
            elif self.settings.compiler == "clang":
                if self.settings.arch == "x86":
                    return "linux-clang-libc++-32" if self.settings.compiler.libcxx == "libc++" else "linux-clang-32"
                elif self.settings.arch == "x86_64":
                    return "linux-clang-libc++" if self.settings.compiler.libcxx == "libc++" else "linux-clang"

        elif self.settings.os == "Macos":
            return {"clang": "macx-clang",
                    "apple-clang": "macx-clang",
                    "gcc": "macx-g++"}.get(str(self.settings.compiler))

        elif self.settings.os == "iOS":
            if self.settings.compiler == "apple-clang":
                return "macx-ios-clang"

        elif self.settings.os == "watchOS":
            if self.settings.compiler == "apple-clang":
                return "macx-watchos-clang"

        elif self.settings.os == "tvOS":
            if self.settings.compiler == "apple-clang":
                return "macx-tvos-clang"

        elif self.settings.os == "Android":
            if self.settings.compiler == "clang":
                return "android-clang"

        elif self.settings.os == "Windows":
            return {
                "Visual Studio": "win32-msvc",
                "msvc": "win32-msvc",
                "gcc": "win32-g++",
                "clang": "win32-clang-g++",
            }.get(str(self.settings.compiler))

        elif self.settings.os == "WindowsStore":
            if is_msvc(self):
                if self.settings.compiler == "Visual Studio":
                    msvc_version = str(self.settings.compiler.version)
                else:
                    msvc_version = {
                        "190": "14",
                        "191": "15",
                        "192": "16",
                    }.get(str(self.settings.compiler.version))
                return {
                    "14": {
                        "armv7": "winrt-arm-msvc2015",
                        "x86": "winrt-x86-msvc2015",
                        "x86_64": "winrt-x64-msvc2015",
                    },
                    "15": {
                        "armv7": "winrt-arm-msvc2017",
                        "x86": "winrt-x86-msvc2017",
                        "x86_64": "winrt-x64-msvc2017",
                    },
                    "16": {
                        "armv7": "winrt-arm-msvc2019",
                        "x86": "winrt-x86-msvc2019",
                        "x86_64": "winrt-x64-msvc2019",
                    }
                }.get(msvc_version).get(str(self.settings.arch))

        elif self.settings.os == "FreeBSD":
            return {"clang": "freebsd-clang",
                    "gcc": "freebsd-g++"}.get(str(self.settings.compiler))

        elif self.settings.os == "SunOS":
            if self.settings.compiler == "sun-cc":
                if self.settings.arch == "sparc":
                    return "solaris-cc-stlport" if self.settings.compiler.libcxx == "libstlport" else "solaris-cc"
                elif self.settings.arch == "sparcv9":
                    return "solaris-cc64-stlport" if self.settings.compiler.libcxx == "libstlport" else "solaris-cc64"
            elif self.settings.compiler == "gcc":
                return {"sparc": "solaris-g++",
                        "sparcv9": "solaris-g++-64"}.get(str(self.settings.arch))
        elif self.settings.os == "Neutrino" and self.settings.compiler == "qcc":
            return {"armv8": "qnx-aarch64le-qcc",
                    "armv8.3": "qnx-aarch64le-qcc",
                    "armv7": "qnx-armle-v7-qcc",
                    "armv7hf": "qnx-armle-v7-qcc",
                    "armv7s": "qnx-armle-v7-qcc",
                    "armv7k": "qnx-armle-v7-qcc",
                    "x86": "qnx-x86-qcc",
                    "x86_64": "qnx-x86-64-qcc"}.get(str(self.settings.arch))
        elif self.settings.os == "Emscripten" and self.settings.arch == "wasm":
            return "wasm-emscripten"

        return None

    def build(self):
        args = ["-confirm-license", "-silent", "-nomake examples", "-nomake tests",
                f"-prefix {self.package_folder}"]
        args.append("-v")
        # args.append("-archdatadir  %s" % os.path.join(self.package_folder, "bin", "archdatadir"))
        # args.append("-datadir  %s" % os.path.join(self.package_folder, "bin", "datadir"))
        # args.append("-sysconfdir  %s" % os.path.join(self.package_folder, "bin", "sysconfdir"))
        args.append("-opensource")
        if self.settings.os == "Windows":
            args.append("-mp")
        if not self.options.shared:
            args.insert(0, "-static")
            if is_msvc(self) and "MT" in msvc_runtime_flag(self):
                args.append("-static-runtime")
        else:
            args.insert(0, "-shared")
        if self.options.multiconfiguration:
            args.append("-debug-and-release")
        elif self.settings.build_type == "Debug":
            args.append("-debug")
        elif self.settings.build_type == "Release":
            args.append("-release")
        elif self.settings.build_type == "RelWithDebInfo":
            args.append("-release")
            args.append("-force-debug-info")
        elif self.settings.build_type == "MinSizeRel":
            args.append("-release")
            args.append("-optimize-size")

        for module in self._submodules:
            args.append("-skip " + module)

        args.append("-qt-zlib")

        # openGL
        opengl = self.options.get_safe("opengl", "no")
        if opengl == "no":
            args += ["-no-opengl"]
        elif opengl == "es2":
            args += ["-opengl es2"]
        elif opengl == "desktop":
            args += ["-opengl desktop"]
        elif opengl == "dynamic":
            args += ["-opengl dynamic"]

        # openSSL
        args += ["-no-openssl"]

        args.append("-no-glib")
        args.append("-qt-pcre")
        args.append("-no-fontconfig")
        args.append("-no-icu")
        args.append("-no-zstd")

        # args.append("--alsa=no")
        # args.append("--no-gstreamer")
        # args.append("--no-pulseaudio")

        args.append("-no-dbus")
        args.append("-no-feature-gssapi")

        args.append("-qt-doubleconversion")
        args.append("-qt-freetype")
        args.append("-qt-harfbuzz")
        args.append("-qt-libjpeg")
        args.append("-qt-libpng")
        args.append("-qt-sqlite")
        args.append("-sql-sqlite")
        args.append("-qt-libmd4c")
        # args.append("-qt-tiff")
        # args.append("-qt-webp")

        libmap = [("zlib", "ZLIB"),
                  ("openssl", "OPENSSL"),
                  ("pcre2", "PCRE2"),
                  ("glib", "GLIB"),
                  ("double-conversion", "DOUBLECONVERSION"),
                  ("freetype", "FREETYPE"),
                  ("fontconfig", "FONTCONFIG"),
                  ("icu", "ICU"),
                  ("harfbuzz", "HARFBUZZ"),
                  ("libjpeg", "LIBJPEG"),
                  ("libjpeg-turbo", "LIBJPEG"),
                  ("libpng", "LIBPNG"),
                  ("libmysqlclient", "MYSQL"),
                  ("libpq", "PSQL"),
                  ("odbc", "ODBC"),
                  ("sdl2", "SDL2"),
                  ("openal", "OPENAL"),
                  ("zstd", "ZSTD"),
                  ("libalsa", "ALSA"),
                  ("xkbcommon", "XKBCOMMON"),
                  ("md4c", "LIBMD4C")]
        for package, var in libmap:
            if package in self.deps_cpp_info.deps:
                if package == "freetype":
                    args.append("\"%s_INCDIR=%s\"" % (var, self.deps_cpp_info[package].include_paths[-1]))

                args.append("\"%s_LIBS=%s\"" % (var, " ".join(self._gather_libs(package))))

        for package in self.deps_cpp_info.deps:
            args += [f"-I \"{s}\"" for s in self.deps_cpp_info[package].include_paths]
            args += [f"-D {s}" for s in self.deps_cpp_info[package].defines]
        args.append("QMAKE_LIBDIR+=\"%s\"" % " ".join(l for package in self.deps_cpp_info.deps for l in self.deps_cpp_info[package].lib_paths))
        if not is_msvc(self):
            args.append("QMAKE_RPATHLINKDIR+=\"%s\"" % ":".join(l for package in self.deps_cpp_info.deps for l in self.deps_cpp_info[package].lib_paths))

        if "libmysqlclient" in self.deps_cpp_info.deps:
            args.append("-mysql_config \"%s\"" % os.path.join(self.deps_cpp_info["libmysqlclient"].rootpath, "bin", "mysql_config"))
        if "libpq" in self.deps_cpp_info.deps:
            args.append("-psql_config \"%s\"" % os.path.join(self.deps_cpp_info["libpq"].rootpath, "bin", "pg_config"))
        if self.settings.os == "Macos":
            args += ["-no-framework"]
            if self.settings.arch == "armv8":
                args.append('QMAKE_APPLE_DEVICE_ARCHS="arm64"')
        elif self.settings.os == "Android":
            args += [f"-android-ndk-platform android-{self.settings.os.api_level}"]
            args += ["-android-abis %s" % {"armv7": "armeabi-v7a",
                                           "armv8": "arm64-v8a",
                                           "x86": "x86",
                                           "x86_64": "x86_64"}.get(str(self.settings.arch))]

        if self.settings.get_safe("compiler.libcxx") == "libstdc++":
            args += ["-D_GLIBCXX_USE_CXX11_ABI=0"]
        elif self.settings.get_safe("compiler.libcxx") == "libstdc++11":
            args += ["-D_GLIBCXX_USE_CXX11_ABI=1"]

        if self.options.sysroot:
            args += [f"-sysroot {self.options.sysroot}"]

        if self.options.device:
            args += [f"-device {self.options.device}"]
        else:
            xplatform_val = self._xplatform()
            if xplatform_val:
                if not cross_building(self, skip_x64_x86=True):
                    args += [f"-platform {xplatform_val}"]
                else:
                    args += [f"-xplatform {xplatform_val}"]
            else:
                self.output.warn("host not supported: %s %s %s %s" %
                                 (self.settings.os, self.settings.compiler,
                                  self.settings.compiler.version, self.settings.arch))
        if self.options.cross_compile:
            args += [f"-device-option CROSS_COMPILE={self.options.cross_compile}"]

        def _getenvpath(var):
            val = os.getenv(var)
            if val and self._settings_build.os == "Windows":
                val = val.replace("\\", "/")
                os.environ[var] = val
            return val

        if not is_msvc(self):
            value = _getenvpath("CC")
            if value:
                args += ['QMAKE_CC="' + value + '"',
                         'QMAKE_LINK_C="' + value + '"',
                         'QMAKE_LINK_C_SHLIB="' + value + '"']

            value = _getenvpath('CXX')
            if value:
                args += ['QMAKE_CXX="' + value + '"',
                         'QMAKE_LINK="' + value + '"',
                         'QMAKE_LINK_SHLIB="' + value + '"']

        if self._settings_build.os == "Linux" and self.settings.compiler == "clang":
            args += ['QMAKE_CXXFLAGS+="-ftemplate-depth=1024"']

        os.mkdir("build_folder")
        with chdir(self, "build_folder"):
            with tools.vcvars(self) if is_msvc(self) else tools.no_op():
                build_env = {"MAKEFLAGS": f"j{build_jobs(self)}", "PKG_CONFIG_PATH": [self.build_folder]}
                if self.settings.os == "Windows":
                    build_env["PATH"] = [os.path.join(self.source_folder, "qt5", "gnuwin32", "bin")]

                with tools.environment_append(build_env):

                    if self._settings_build.os == "Macos":
                        save(self, ".qmake.stash" , "")
                        save(self, ".qmake.super" , "")

                    self.run("%s/qt5/configure %s" % (self.source_folder, " ".join(args)), run_environment=True)
                    if self._settings_build.os == "Macos":
                        save(self, "bash_env", 'export DYLD_LIBRARY_PATH="%s"' % ":".join(RunEnvironment(self).vars["DYLD_LIBRARY_PATH"]))
                    with tools.environment_append({
                        "BASH_ENV": os.path.abspath("bash_env")
                    }) if self._settings_build.os == "Macos" else tools.no_op():
                        self.run(self._make_program(), run_environment=True)

    @property
    def _cmake_core_extras_file(self):
        return os.path.join("lib", "cmake", "Qt5Core", "conan_qt_core_extras.cmake")

    def _cmake_qt5_private_file(self, module):
        return os.path.join("lib", "cmake", f"Qt5{module}", f"conan_qt_qt5_{module.lower()}private.cmake")

    def package(self):
        with chdir(self, "build_folder"):
            self.run(f"{self._make_program()} install")
        save(self, os.path.join(self.package_folder, "bin", "qt.conf"), """[Paths]
Prefix = ..
""")
        self.copy("*LICENSE*", src="qt5/", dst="licenses")
        for module in self._submodules:
            rmdir(self, os.path.join(self.package_folder, "licenses", module))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        for mask in ["Find*.cmake", "*Config.cmake", "*-config.cmake"]:
            rm(self, mask, self.package_folder, recursive=True)
        rm(self, "*.la*", os.path.join(self.package_folder, "lib"), recursive=True)
        rm(self, "*.pdb*", os.path.join(self.package_folder, "lib"), recursive=True)
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"), recursive=True)
        # "Qt5Bootstrap" is internal Qt library - removing it to avoid linking error, since it contains
        # symbols that are also in "Qt5Core.lib". It looks like there is no "Qt5Bootstrap.dll".
        for fl in glob.glob(os.path.join(self.package_folder, "lib", "*Qt5Bootstrap*")):
            os.remove(fl)

        for m in os.listdir(os.path.join(self.package_folder, "lib", "cmake")):
            module = os.path.join(self.package_folder, "lib", "cmake", m, f"{m}Macros.cmake")
            if not os.path.isfile(module):
                rmdir(self, os.path.join(self.package_folder, "lib", "cmake", m))

        extension = ""
        if self._settings_build.os == "Windows":
            extension = ".exe"
        v = Version(self.version)
        filecontents = textwrap.dedent(f"""\
            set(QT_CMAKE_EXPORT_NAMESPACE Qt5)
            set(QT_VERSION_MAJOR {v.major})
            set(QT_VERSION_MINOR {v.minor})
            set(QT_VERSION_PATCH {v.patch})
        """)
        targets = {}
        targets["Core"] = ["moc", "rcc", "qmake"]
        targets["DBus"] = ["qdbuscpp2xml", "qdbusxml2cpp"]
        targets["Widgets"] = ["uic"]

        # self.options.qttools:
        targets["Tools"] = ["qhelpgenerator", "qcollectiongenerator", "qdoc", "qtattributionsscanner"]
        targets[""] = ["lconvert", "lrelease", "lupdate"]
        # self.options.qttools:

        for namespace, targets in targets.items():
            for target in targets:
                filecontents += textwrap.dedent("""\
                    if(NOT TARGET ${{QT_CMAKE_EXPORT_NAMESPACE}}::{target})
                        add_executable(${{QT_CMAKE_EXPORT_NAMESPACE}}::{target} IMPORTED)
                        set_target_properties(${{QT_CMAKE_EXPORT_NAMESPACE}}::{target} PROPERTIES IMPORTED_LOCATION ${{CMAKE_CURRENT_LIST_DIR}}/../../../bin/{target}{ext})
                        set(Qt5{namespace}_{uppercase_target}_EXECUTABLE ${{QT_CMAKE_EXPORT_NAMESPACE}}::{target})
                    endif()
                    """.format(target=target, ext=extension, namespace=namespace, uppercase_target=target.upper()))

        if self.settings.os == "Windows":
            filecontents += textwrap.dedent("""\
                set(Qt5Core_QTMAIN_LIBRARIES Qt5::WinMain)
                if (NOT Qt5_NO_LINK_QTMAIN)
                    set(_isExe $<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>)
                    set(_isWin32 $<BOOL:$<TARGET_PROPERTY:WIN32_EXECUTABLE>>)
                    set(_isNotExcluded $<NOT:$<BOOL:$<TARGET_PROPERTY:Qt5_NO_LINK_QTMAIN>>>)
                    set(_isPolicyNEW $<TARGET_POLICY:CMP0020>)
                    set_property(TARGET Qt5::Core APPEND PROPERTY
                        INTERFACE_LINK_LIBRARIES
                            $<$<AND:${_isExe},${_isWin32},${_isNotExcluded},${_isPolicyNEW}>:Qt5::WinMain>
                    )
                    unset(_isExe)
                    unset(_isWin32)
                    unset(_isNotExcluded)
                    unset(_isPolicyNEW)
                endif()
                """)

        filecontents += textwrap.dedent(f"""\
            if(NOT DEFINED QT_DEFAULT_MAJOR_VERSION)
                set(QT_DEFAULT_MAJOR_VERSION {v.major})
            endif()
            """)
        filecontents += 'set(CMAKE_AUTOMOC_MACRO_NAMES "Q_OBJECT" "Q_GADGET" "Q_GADGET_EXPORT" "Q_NAMESPACE" "Q_NAMESPACE_EXPORT")\n'
        save(self, os.path.join(self.package_folder, self._cmake_core_extras_file), filecontents)

        def _create_private_module(module, dependencies=[]):
            if "Core" not in dependencies:
                dependencies.append("Core")
            dependencies_string = ';'.join(f'Qt5::{dependency}' for dependency in dependencies)
            contents = textwrap.dedent("""\
            if(NOT TARGET Qt5::{0}Private)
                add_library(Qt5::{0}Private INTERFACE IMPORTED)
                set_target_properties(Qt5::{0}Private PROPERTIES
                    INTERFACE_INCLUDE_DIRECTORIES "${{CMAKE_CURRENT_LIST_DIR}}/../../../include/Qt{0}/{1};${{CMAKE_CURRENT_LIST_DIR}}/../../../include/Qt{0}/{1}/Qt{0}"
                    INTERFACE_LINK_LIBRARIES "{2}"
                )

                add_library(Qt::{0}Private INTERFACE IMPORTED)
                set_target_properties(Qt::{0}Private PROPERTIES
                    INTERFACE_LINK_LIBRARIES "Qt5::{0}Private"
                    _qt_is_versionless_target "TRUE"
                )
            endif()""".format(module, self.version, dependencies_string))

            save(self, os.path.join(self.package_folder, self._cmake_qt5_private_file(module)), contents)

        _create_private_module("Core")
        _create_private_module("Gui", ["CorePrivate", "Gui"])
        _create_private_module("Widgets", ["CorePrivate", "Gui", "GuiPrivate"])

    def package_id(self):
        del self.info.options.cross_compile
        del self.info.options.sysroot
        if self.options.multiconfiguration and is_msvc(self):
            if self.settings.compiler == "Visual Studio":
                if "MD" in self.settings.compiler.runtime:
                    self.info.settings.compiler.runtime = "MD/MDd"
                else:
                    self.info.settings.compiler.runtime = "MT/MTd"
            else:
                self.info.settings.compiler.runtime_type = "Release/Debug"

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Qt5")

        self.cpp_info.names["cmake_find_package"] = "Qt5"
        self.cpp_info.names["cmake_find_package_multi"] = "Qt5"

        build_modules = {}

        def _add_build_module(component, module):
            if component not in build_modules:
                build_modules[component] = []
            build_modules[component].append(module)
            self.cpp_info.components[component].build_modules["cmake_find_package"].append(module)
            self.cpp_info.components[component].build_modules["cmake_find_package_multi"].append(module)

        libsuffix = ""
        if not self.options.multiconfiguration:
            if self.settings.build_type == "Debug":
                if self.settings.os == "Windows" and is_msvc(self):
                    libsuffix = "d"
                elif is_apple_os(self):
                    libsuffix = "_debug"

        def _get_corrected_reqs(requires):
            reqs = []
            for r in requires:
                reqs.append(r if "::" in r else f"qt{r}")
            return reqs

        def _create_module(module, requires=[], has_include_dir=True):
            componentname = f"qt{module}"
            assert componentname not in self.cpp_info.components, f"Module {module} already present in self.cpp_info.components"
            self.cpp_info.components[componentname].set_property("cmake_target_name", f"Qt5::{module}")
            self.cpp_info.components[componentname].names["cmake_find_package"] = module
            self.cpp_info.components[componentname].names["cmake_find_package_multi"] = module
            if module.endswith("Private"):
                libname = module[:-7]
            else:
                libname = module
            self.cpp_info.components[componentname].libs = [f"Qt5{libname}{libsuffix}"]
            if has_include_dir:
                self.cpp_info.components[componentname].includedirs = ["include", os.path.join("include", f"Qt{module}")]
            self.cpp_info.components[componentname].defines = [f"QT_{module.upper()}_LIB"]
            if module != "Core" and "Core" not in requires:
                requires.append("Core")
            self.cpp_info.components[componentname].requires = _get_corrected_reqs(requires)

        def _create_plugin(pluginname, libname, plugintype, requires):
            componentname = f"qt{pluginname}"
            assert componentname not in self.cpp_info.components, f"Plugin {pluginname} already present in self.cpp_info.components"
            self.cpp_info.components[componentname].set_property("cmake_target_name", f"Qt5::{pluginname}")
            self.cpp_info.components[componentname].names["cmake_find_package"] = pluginname
            self.cpp_info.components[componentname].names["cmake_find_package_multi"] = pluginname
            if not self.options.shared:
                self.cpp_info.components[componentname].libs = [libname + libsuffix]
            self.cpp_info.components[componentname].libdirs = [os.path.join("plugins", plugintype)]
            self.cpp_info.components[componentname].includedirs = []
            if "Core" not in requires:
                requires.append("Core")
            self.cpp_info.components[componentname].requires = _get_corrected_reqs(requires)

        _create_module("Core")
        if self.settings.os == "Windows":
            module = "WinMain"
            componentname = f"qt{module}"
            self.cpp_info.components[componentname].set_property("cmake_target_name", f"Qt5::{module}")
            self.cpp_info.components[componentname].names["cmake_find_package"] = module
            self.cpp_info.components[componentname].names["cmake_find_package_multi"] = module
            self.cpp_info.components[componentname].libs = [f"qtmain{libsuffix}"]
            self.cpp_info.components[componentname].includedirs = []
            self.cpp_info.components[componentname].defines = []

        # self.options.gui begin
        _create_module("Gui")
        _add_build_module("qtGui", self._cmake_qt5_private_file("Gui"))

        event_dispatcher_reqs = ["Core", "Gui"]
        _create_module("EventDispatcherSupport", event_dispatcher_reqs)
        _create_module("FontDatabaseSupport", ["Core", "Gui"])
        if self.settings.os == "Windows":
            self.cpp_info.components["qtFontDatabaseSupport"].system_libs.extend(["advapi32", "ole32", "user32", "gdi32"])
        elif is_apple_os(self):
            self.cpp_info.components["qtFontDatabaseSupport"].frameworks.extend(["CoreFoundation", "CoreGraphics", "CoreText","Foundation"])
            self.cpp_info.components["qtFontDatabaseSupport"].frameworks.append("AppKit" if self.settings.os == "Macos" else "UIKit")

        _create_module("ThemeSupport", ["Core", "Gui"])
        _create_module("AccessibilitySupport", ["Core", "Gui"])

        if is_apple_os(self):
            _create_module("ClipboardSupport", ["Core", "Gui"])
            self.cpp_info.components["qtClipboardSupport"].frameworks = ["ImageIO"]
            if self.settings.os == "Macos":
                self.cpp_info.components["qtClipboardSupport"].frameworks.append("AppKit")
            _create_module("GraphicsSupport", ["Core", "Gui"])

        if self.settings.os in ["Android", "Emscripten"]:
            _create_module("EglSupport", ["Core", "Gui"])

        if self.settings.os == "Windows":
            windows_reqs = ["Core", "Gui"]
            windows_reqs.extend(["EventDispatcherSupport", "FontDatabaseSupport", "ThemeSupport", "AccessibilitySupport"])
            _create_module("WindowsUIAutomationSupport", ["Core", "Gui"])
            windows_reqs.append("WindowsUIAutomationSupport")
            _create_plugin("QWindowsIntegrationPlugin", "qwindows", "platforms", windows_reqs)
            _create_plugin("QWindowsVistaStylePlugin", "qwindowsvistastyle", "styles", windows_reqs)
            self.cpp_info.components["qtQWindowsIntegrationPlugin"].system_libs = ["advapi32", "dwmapi", "gdi32", "imm32",
                "ole32", "oleaut32", "shell32", "shlwapi", "user32", "winmm", "winspool", "wtsapi32"]
        elif self.settings.os == "Android":
            android_reqs = ["Core", "Gui", "EventDispatcherSupport", "AccessibilitySupport", "FontDatabaseSupport", "EglSupport"]
            _create_plugin("QAndroidIntegrationPlugin", "qtforandroid", "platforms", android_reqs)
            self.cpp_info.components["qtQAndroidIntegrationPlugin"].system_libs = ["android", "jnigraphics"]
        elif self.settings.os == "Macos":
            cocoa_reqs = ["Core", "Gui", "ClipboardSupport", "ThemeSupport", "FontDatabaseSupport", "GraphicsSupport", "AccessibilitySupport"]
            cocoa_reqs.append("PrintSupport")
            _create_plugin("QCocoaIntegrationPlugin", "qcocoa", "platforms", cocoa_reqs)
            _create_plugin("QMacStylePlugin", "qmacstyle", "styles", cocoa_reqs)
            self.cpp_info.components["QCocoaIntegrationPlugin"].frameworks = ["AppKit", "Carbon", "CoreServices", "CoreVideo",
                "IOKit", "IOSurface", "Metal", "QuartzCore"]
        elif self.settings.os in ["iOS", "tvOS"]:
            _create_plugin("QIOSIntegrationPlugin", "qios", "platforms", ["ClipboardSupport", "FontDatabaseSupport", "GraphicsSupport"])
            self.cpp_info.components["QIOSIntegrationPlugin"].frameworks = ["AudioToolbox", "Foundation", "Metal",
                "MobileCoreServices", "OpenGLES", "QuartzCore", "UIKit"]
        elif self.settings.os == "watchOS":
            _create_plugin("QMinimalIntegrationPlugin", "qminimal", "platforms", ["EventDispatcherSupport", "FontDatabaseSupport"])
        elif self.settings.os == "Emscripten":
            _create_plugin("QWasmIntegrationPlugin", "qwasm", "platforms", ["Core", "Gui", "EventDispatcherSupport", "FontDatabaseSupport", "EglSupport"])
        elif self.settings.os in ["Linux", "FreeBSD"]:
            service_support_reqs = ["Core", "Gui"]
            _create_module("ServiceSupport", service_support_reqs)
            _create_module("EdidSupport")
            _create_module("XkbCommonSupport", ["Core", "Gui"])
            xcb_qpa_reqs = ["Core", "Gui", "ServiceSupport", "ThemeSupport", "FontDatabaseSupport", "EdidSupport", "XkbCommonSupport"]
            _create_module("XcbQpa", xcb_qpa_reqs, has_include_dir=False)
            _create_plugin("QXcbIntegrationPlugin", "qxcb", "platforms", ["Core", "Gui", "XcbQpa"])
        # self.options.gui end

        _create_module("Network")
        _create_module("Sql")
        _create_module("Test")

        _create_module("Widgets", ["Gui"])
        _add_build_module("qtWidgets", self._cmake_qt5_private_file("Widgets"))

        if self.settings.os not in ["iOS", "watchOS", "tvOS"]:
            _create_module("PrintSupport", ["Gui", "Widgets"])
            if self.settings.os == "Macos" and not self.options.shared:
                self.cpp_info.components["PrintSupport"].system_libs.append("cups")
        if self.options.get_safe("opengl", "no") != "no":
            _create_module("OpenGL", ["Gui"])
        if self.options.get_safe("opengl", "no") != "no":
            _create_module("OpenGLExtensions", ["Gui"])
        _create_module("Concurrent")
        _create_module("Xml")

        # self.options.qttools
        self.cpp_info.components["qtLinguistTools"].set_property("cmake_target_name", "Qt5::LinguistTools")
        self.cpp_info.components["qtLinguistTools"].names["cmake_find_package"] = "LinguistTools"
        self.cpp_info.components["qtLinguistTools"].names["cmake_find_package_multi"] = "LinguistTools"
        _create_module("UiPlugin", ["Gui", "Widgets"])
        self.cpp_info.components["qtUiPlugin"].libs = [] # this is a collection of abstract classes, so this is header-only
        self.cpp_info.components["qtUiPlugin"].libdirs = []
        _create_module("UiTools", ["UiPlugin", "Gui", "Widgets"])
        if not cross_building(self):
            _create_module("Designer", ["Gui", "UiPlugin", "Widgets", "Xml"])
        _create_module("Help", ["Gui", "Sql", "Widgets"])
        # self.options.qttools

        if self.settings.os != "Windows":
            self.cpp_info.components["qtCore"].cxxflags.append("-fPIC")

        if not self.options.shared:
            if self.settings.os == "Windows":
                self.cpp_info.components["qtCore"].system_libs.append("version")  # qtcore requires "GetFileVersionInfoW" and "VerQueryValueW" which are in "Version.lib" library
                self.cpp_info.components["qtCore"].system_libs.append("winmm")    # qtcore requires "__imp_timeSetEvent" which is in "Winmm.lib" library
                self.cpp_info.components["qtCore"].system_libs.append("netapi32") # qtcore requires "NetApiBufferFree" which is in "Netapi32.lib" library
                self.cpp_info.components["qtCore"].system_libs.append("userenv")  # qtcore requires "__imp_GetUserProfileDirectoryW " which is in "UserEnv.Lib" library
                self.cpp_info.components["qtCore"].system_libs.append("ws2_32")  # qtcore requires "WSAStartup " which is in "Ws2_32.Lib" library
                self.cpp_info.components["qtNetwork"].system_libs.append("dnsapi")  # qtnetwork from qtbase requires "DnsFree" which is in "Dnsapi.lib" library
                self.cpp_info.components["qtNetwork"].system_libs.append("iphlpapi")
                self.cpp_info.components["qtWidgets"].system_libs.append("UxTheme")
                self.cpp_info.components["qtWidgets"].system_libs.append("dwmapi")

            if is_apple_os(self):
                self.cpp_info.components["qtCore"].frameworks.append("CoreServices" if self.settings.os == "Macos" else "MobileCoreServices")
                self.cpp_info.components["qtNetwork"].frameworks.append("SystemConfiguration")
                self.cpp_info.components["qtNetwork"].frameworks.append("Security")
            if self.settings.os == "Macos":
                self.cpp_info.components["qtCore"].frameworks.append("IOKit")     # qtcore requires "_IORegistryEntryCreateCFProperty", "_IOServiceGetMatchingService" and much more which are in "IOKit" framework
                self.cpp_info.components["qtCore"].frameworks.append("Cocoa")     # qtcore requires "_OBJC_CLASS_$_NSApplication" and more, which are in "Cocoa" framework
                self.cpp_info.components["qtCore"].frameworks.append("Security")  # qtcore requires "_SecRequirementCreateWithString" and more, which are in "Security" framework

        # self.cpp_info.components["qtCore"].builddirs.append(os.path.join("bin","archdatadir","bin"))
        _add_build_module("qtCore", self._cmake_core_extras_file)
        _add_build_module("qtCore", self._cmake_qt5_private_file("Core"))

        for m in os.listdir(os.path.join("lib", "cmake")):
            module = os.path.join("lib", "cmake", m, f"{m}Macros.cmake")
            component_name = m.replace("Qt5", "qt")
            if os.path.isfile(module):
                _add_build_module(component_name, module)
            self.cpp_info.components[component_name].builddirs.append(os.path.join("lib", "cmake", m))

        qt5core_config_extras_mkspec_dir_cmake = load(self,
            os.path.join("lib", "cmake", "Qt5Core", "Qt5CoreConfigExtrasMkspecDir.cmake"))
        mkspecs_dir_begin = qt5core_config_extras_mkspec_dir_cmake.find("mkspecs/")
        mkspecs_dir_end = qt5core_config_extras_mkspec_dir_cmake.find("\"", mkspecs_dir_begin)
        mkspecs_dir = qt5core_config_extras_mkspec_dir_cmake[mkspecs_dir_begin:mkspecs_dir_end].split('/')
        mkspecs_path = os.path.join(*mkspecs_dir)
        assert os.path.exists(mkspecs_path)
        self.cpp_info.components["qtCore"].includedirs.append(mkspecs_path)

        objects_dirs = glob.glob(os.path.join(self.package_folder, "lib", "objects-*/"))
        for object_dir in objects_dirs:
            for m in os.listdir(object_dir):
                component = "qt" + m[:m.find("_")]
                if component not in self.cpp_info.components:
                    continue
                submodules_dir = os.path.join(object_dir, m)
                for sub_dir in os.listdir(submodules_dir):
                    submodule_dir = os.path.join(submodules_dir, sub_dir)
                    obj_files = [os.path.join(submodule_dir, file) for file in os.listdir(submodule_dir)]
                    self.cpp_info.components[component].exelinkflags.extend(obj_files)
                    self.cpp_info.components[component].sharedlinkflags.extend(obj_files)

        build_modules_list = []

        def _add_build_modules_for_component(component):
            for req in self.cpp_info.components[component].requires:
                if "::" in req: # not a qt component
                    continue
                _add_build_modules_for_component(req)
            build_modules_list.extend(build_modules.pop(component, []))

        for c in self.cpp_info.components:
            _add_build_modules_for_component(c)

        self.cpp_info.set_property("cmake_build_modules", build_modules_list)

    @staticmethod
    def _remove_duplicate(l):
        seen = set()
        seen_add = seen.add
        for element in itertools.filterfalse(seen.__contains__, l):
            seen_add(element)
            yield element

    def _gather_libs(self, p):
        if p not in self.deps_cpp_info.deps:
            return []
        libs = ["-l" + i for i in self.deps_cpp_info[p].libs + self.deps_cpp_info[p].system_libs]
        if is_apple_os(self):
            libs += ["-framework " + i for i in self.deps_cpp_info[p].frameworks]
        libs += self.deps_cpp_info[p].sharedlinkflags
        for dep in self.deps_cpp_info[p].public_deps:
            libs += self._gather_libs(dep)
        return self._remove_duplicate(libs)
