cd recipes/ceres-solver
conan create all/conanfile.py ceres-solver/1.13.0@ -pr:b=default -pr:h=default

cd recipes/cli11
conan create all/conanfile.py cli11/1.9.1@ -pr:b=default -pr:h=default

cd recipes/opencv
conan create 3.x/conanfile.py opencv/3.4.12@ -pr:b=default -pr:h=default
