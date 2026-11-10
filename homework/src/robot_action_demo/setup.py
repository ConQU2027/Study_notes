from setuptools import find_packages, setup

package_name = 'robot_action_demo'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ting',
    maintainer_email='ting@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'action_client = robot_action_demo.action_client:main',
            'action_car = robot_action_demo.action_car:main',
            'action_car_param = robot_action_demo.action_car_param:main'
        ],
    },
)
