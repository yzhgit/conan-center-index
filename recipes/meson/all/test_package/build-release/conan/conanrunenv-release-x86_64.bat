@echo off
setlocal
echo @echo off > "E:\OpenSource\conan-center-private\recipes\meson\all\test_package\build-release\conan\deactivate_conanrunenv-release-x86_64.bat"
echo echo Restoring environment >> "E:\OpenSource\conan-center-private\recipes\meson\all\test_package\build-release\conan\deactivate_conanrunenv-release-x86_64.bat"
for %%v in () do (
    set foundenvvar=
    for /f "delims== tokens=1,2" %%a in ('set') do (
        if /I "%%a" == "%%v" (
            echo set "%%a=%%b">> "E:\OpenSource\conan-center-private\recipes\meson\all\test_package\build-release\conan\deactivate_conanrunenv-release-x86_64.bat"
            set foundenvvar=1
        )
    )
    if not defined foundenvvar (
        echo set %%v=>> "E:\OpenSource\conan-center-private\recipes\meson\all\test_package\build-release\conan\deactivate_conanrunenv-release-x86_64.bat"
    )
)
endlocal

