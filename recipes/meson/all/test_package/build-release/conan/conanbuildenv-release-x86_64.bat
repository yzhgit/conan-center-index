@echo off
setlocal
echo @echo off > "E:\OpenSource\conan-center-private\recipes\meson\all\test_package\build-release\conan\deactivate_conanbuildenv-release-x86_64.bat"
echo echo Restoring environment >> "E:\OpenSource\conan-center-private\recipes\meson\all\test_package\build-release\conan\deactivate_conanbuildenv-release-x86_64.bat"
for %%v in (PATH) do (
    set foundenvvar=
    for /f "delims== tokens=1,2" %%a in ('set') do (
        if /I "%%a" == "%%v" (
            echo set "%%a=%%b">> "E:\OpenSource\conan-center-private\recipes\meson\all\test_package\build-release\conan\deactivate_conanbuildenv-release-x86_64.bat"
            set foundenvvar=1
        )
    )
    if not defined foundenvvar (
        echo set %%v=>> "E:\OpenSource\conan-center-private\recipes\meson\all\test_package\build-release\conan\deactivate_conanbuildenv-release-x86_64.bat"
    )
)
endlocal


set "PATH=D:\conan\data\meson\0.59.3\_\_\package\5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9\bin;D:\conan\data\ninja\1.11.1\_\_\package\0a420ff5c47119e668867cdb51baff0eca1fdb68\bin;%PATH%"