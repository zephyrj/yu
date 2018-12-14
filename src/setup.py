import setuptools

setuptools.setup(
    name="yu",
    version="0.0.1",
    author="Jon Sykes",
    author_email="jono.sykes15@gmail.com",
    description="Python library for home network management",
    url="https://github.com/zephyrj/yu",
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=['paramiko', 'pathlib', ],
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)
