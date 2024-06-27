from setuptools import setup, find_packages

setup(
    name='MowerControl',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'requests',
        'schedule',
        'pytz',
        'Flask',
    ],
    entry_points={
        'console_scripts': [
            'mower_control=path.to.your.module:main_function',
        ],
    },
    author='RyroNZ',
    author_email='ryronz@gmail.com',
    description='A control system for Husqvarna Mower with weather-based control and scheduling.',
    url='https://github.com/yourusername/yourrepository',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
