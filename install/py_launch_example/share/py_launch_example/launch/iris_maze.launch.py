import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessStart
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    """Generate a launch description for an iris quadcopter."""
    pkg_py_launch_example = get_package_share_directory("py_launch_example")
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")

    # Ensure `SDF_PATH` is populated as `sdformat_urdf` uses this rather
    # than `GZ_SIM_RESOURCE_PATH` to locate resources.
    if "GZ_SIM_RESOURCE_PATH" in os.environ:
        gz_sim_resource_path = os.environ["GZ_SIM_RESOURCE_PATH"]

        if "SDF_PATH" in os.environ:
            sdf_path = os.environ["SDF_PATH"]
            os.environ["SDF_PATH"] = sdf_path + ":" + gz_sim_resource_path
        else:
            os.environ["SDF_PATH"] = gz_sim_resource_path

    # Load SDF file.
    # sdf_file = os.path.join(pkg_py_launch_example, "models", "iris_with_lidar", "model.sdf")
    # with open(sdf_file, "r") as infp:
    #     robot_desc = infp.read()


    urdf_file = os.path.join(pkg_py_launch_example, "urdf", "iris_placeholder.urdf")
    with open(urdf_file, "r") as urdf_infp:
        robot_urdf_desc = urdf_infp.read()
    # Gazebo simulation.
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={
           'gz_args': '-r ' + os.path.join(pkg_py_launch_example, 'worlds', 'iris_maze.sdf')
        }.items(),
    )

    # RViz.
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        arguments=[
            "-d",
            os.path.join(pkg_py_launch_example, "rviz", "iris_with_lidar.rviz"),
        ],
        condition=IfCondition(LaunchConfiguration("rviz")),
    )


    #     #joint state publisher
    joint_state_publisher_gui = Node(
    package='joint_state_publisher_gui',
    executable='joint_state_publisher_gui',
    name='joint_state_publisher_gui',
    arguments=[urdf_file],
    output=['screen']
    )

    # Robot state publisher.
    # robot_state_publisher = Node(
    #     package="robot_state_publisher",
    #     executable="robot_state_publisher",
    #     name="robot_state_publisher",
    #     output="both",
    #     parameters=[
    #         {"robot_description": robot_desc},
    #         {"frame_prefix": ""},
    #     ],
    # )
    robot_state_publisher = Node(
    package="robot_state_publisher",
    executable="robot_state_publisher",
    name="robot_state_publisher",
    output="screen",
    parameters=[
        {"robot_description": robot_urdf_desc},
        {"use_sim_time": True}
    ],
    )


    # Bridge.
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[
            {
                "config_file": os.path.join(
                    pkg_py_launch_example, "config", "iris_lidar_bridge.yaml"
                ),
                "qos_overrides./tf_static.publisher.durability": "transient_local",
            }
        ],
        output="screen",
    )

    # Relay - use instead of transform when Gazebo is only publishing odom -> base_link
    topic_tools_tf = Node(
        package="topic_tools",
        executable="relay",
        arguments=[
            "/gz/tf",
            "/tf",
            "tf2_msgs/msg/TFMessage",
        ],
        output="screen",
        respawn=False,
        condition=IfCondition(LaunchConfiguration("use_gz_tf")),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("rviz", default_value="true", description="Open RViz."),
            DeclareLaunchArgument("use_gz_tf", default_value="true", description="Use Gazebo TF."),
            robot_state_publisher,
            joint_state_publisher_gui,
            bridge,
            RegisterEventHandler(
                OnProcessStart(
                    target_action=bridge,
                    on_start=[topic_tools_tf]
                )
            ),
            rviz,
            gz_sim,
        ]
    )


# #  ExecuteProcess(
# #                 cmd=['gz','sim','-v4','-r'+os.path.join(pkg_py_launch_example, 'worlds', 'iris_maze.sdf')]
#             # )
