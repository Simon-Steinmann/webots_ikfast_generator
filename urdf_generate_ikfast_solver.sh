#!/bin/bash
echo "Enter your RobotName. Make sure you exported your robot as VRML and URDF and placed "
echo "them into the 'webots_ikfast_generator/import/' folder. The two files should be named:"
echo    "MYROBOT_NAME.urdf"
echo "Please select the file from the list"

files=$(ls ./import/*.urdf)
i=1

for j in $files; do
    echo "$i.$j"
    file[i]=${j%.urdf}
    i=$(( i + 1 ))
done

echo "Enter number"
read input
echo "You select the file ${file[$input]}.urdf"
MYROBOT_NAME=$(basename ${file[$input]})
mkdir "./export/$MYROBOT_NAME"
cp "./import/$MYROBOT_NAME.urdf" "./export/$MYROBOT_NAME"
echo "RobotName is '$MYROBOT_NAME'"
echo '-----------------------------'
cd "export/$MYROBOT_NAME"
rosrun collada_urdf urdf_to_collada "$MYROBOT_NAME".urdf "$MYROBOT_NAME".dae
cd ../..
echo '-----------------------------'
echo "DONE! Copying '$MYROBOT_NAME.dae' and  meshes to Docker for conversion"
CONTAINER_ID="$(docker ps -q -l)"
echo "$CONTAINER_ID"
docker cp ./export/$MYROBOT_NAME/ $CONTAINER_ID:/home/
echo "Starting Docker container."
#docker start $CONTAINER_ID  && docker attach `docker ps -q -l`
#alias docbash="docker exec $CONTAINER_ID  /bin/sh -c "
docker exec $CONTAINER_ID  /bin/bash -c "
    export MYROBOT_NAME=$MYROBOT_NAME;  
    source /ros_entrypoint.sh;
    export IKFAST_PRECISION="4";
    cd home/$MYROBOT_NAME;
    rosrun moveit_kinematics round_collada_numbers.py "$MYROBOT_NAME".dae "$MYROBOT_NAME".dae "$IKFAST_PRECISION"
    "
docker exec $CONTAINER_ID  /bin/sh -c "
    cd home/$MYROBOT_NAME;
    openrave-robot.py "$MYROBOT_NAME".dae --info links
    "

echo '-----------------------------'
echo -e "Do you want to compile the ikFast solver now? This may take 10min - 2h!!! (y/n)"
echo -e "If you already compiled the solver, press 'n' to skip this step."
read conf

case $conf in
    [Nn]* ) echo "Skipping ikFast solver compile.";;
    [Yy]* ) 
        echo "--------"
        echo "Specify the index of the base link and the last link of your chain. There have to be exactly 6 movable joints between the two. Fixed joints can be more."
        read -p  "BASE_LINK=" BASE_LINK
        read -p  "EEF_LINK=" EEF_LINK
        docker exec $CONTAINER_ID  /bin/bash -c "
            export BASE_LINK="$BASE_LINK";
            export EEF_LINK="$EEF_LINK"
            "
        IKFAST_OUTPUT_PATH="/home/$MYROBOT_NAME/ikfast61_"$MYROBOT_NAME".cpp"
        #transform6d
        IKTYPE='transform6d' #"translationdirection5d"
        docker exec $CONTAINER_ID  /bin/bash -c "python /opt/ros/indigo/lib/python2.7/dist-packages/openravepy/_openravepy_/ikfast.py --robot=/home/"$MYROBOT_NAME"/"$MYROBOT_NAME".dae --iktype="$IKTYPE" --baselink="$BASE_LINK" --eelink="$EEF_LINK" --savefile="$IKFAST_OUTPUT_PATH"";;
esac



docker cp $CONTAINER_ID:/home/$MYROBOT_NAME/ikfast61_"$MYROBOT_NAME".cpp ./export/$MYROBOT_NAME/
docker cp $CONTAINER_ID:/home/$MYROBOT_NAME/ikfast61_"$MYROBOT_NAME".cpp ./ikfastpy/
echo '-----------------------------'
echo -e "Do you want to compile the ikfastpy wrapper for the converted solver? (y/n)"
echo -e "This only takes up to 1min, press 'n' to skip this step."
read conf
case $conf in
    [Nn]* ) echo "Skipping ikfastpy wrapper  compile.";;
    [Yy]* ) 
        cp ./ikfastpy/ikfast61.cpp ./ikfastpy/ikfast61_backup.cpp 
        rm ./ikfastpy/ikfast61.cpp 
        rm ./ikfastpy/ikfastpy.cpython-37m-x86_64-linux-gnu.so
        cp ./ikfastpy/ikfast61_"$MYROBOT_NAME".cpp ./ikfastpy/ikfast61.cpp        
        cd ikfastpy
        python setup.py build_ext --inplace
        cp ./ikfastpy.cpython* ../export/$MYROBOT_NAME/;;
esac

