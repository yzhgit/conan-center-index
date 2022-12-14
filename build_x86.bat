pushd %~dp0

pushd recipes/benchmark
conan create all/conanfile.py benchmark/1.7.1@ -pr:b=default -pr:h=default
popd

pushd recipes/catch2
conan create 2.x.x/conanfile.py catch2/2.13.9@ -pr:b=default -pr:h=default
popd

pushd recipes/ceres-solver
conan create all/conanfile.py ceres-solver/1.13.0@ -pr:b=default -pr:h=default
popd

pushd recipes/cli11
conan create all/conanfile.py cli11/1.9.1@ -pr:b=default -pr:h=default
popd

pushd recipes/dlib
conan create all/conanfile.py dlib/19.19@ -pr:b=default -pr:h=default
popd

pushd recipes/eigen
conan create all/conanfile.py eigen/3.4.0@ -pr:b=default -pr:h=default
popd

pushd recipes/ghc-filesystem
conan create all/conanfile.py ghc-filesystem/1.5.12@ -pr:b=default -pr:h=default
popd

pushd recipes/nlohmann_json
conan create all/conanfile.py nlohmann_json/3.9.1@ -pr:b=default -pr:h=default
popd

pushd recipes/opencv
conan create 3.x/conanfile.py opencv/3.4.12@ -o opencv:shared=True -pr:b=default -pr:h=default
popd

pushd recipes/stb
conan create all/conanfile.py stb/cci.20220909@ -pr:b=default -pr:h=default
popd

pushd recipes/toml11
conan create all/conanfile.py toml11/3.7.1@ -pr:b=default -pr:h=default
popd

pushd recipes/vcglib
conan create all/conanfile.py vcglib/2020.12@ -pr:b=default -pr:h=default
popd

pushd recipes/ninja
conan create all/conanfile.py ninja/1.11.1@ -pr:b=default -pr:h=default
popd

pushd recipes/meson
conan create all/conanfile.py meson/0.59.3@ -pr:b=default -pr:h=default
popd

pushd recipes/jom
conan create all/conanfile.py jom/1.1.3@ -pr:b=default -pr:h=default
popd

pushd recipes/qt
conan create 5.x.x/conanfile.py qt/5.15.7@ -o qt:shared=True -pr:b=default -pr:h=default --keep-source
REM conan create 5.x.x/conanfile.py qt/5.15.7@ -o qt:shared=True -pr:b=default -pr:h=default --keep-source
popd

popd
