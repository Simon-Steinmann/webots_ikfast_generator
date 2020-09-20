#!/bin/bash

outPath='/home/simon/git/ikfast_pybind/src/'
template="${outPath}abb_irb4600_40_255"
echo $template
files=$(ls ./export/*/*.cpp)
i=1

for j in $files; do
    source[i]=$j
    
    file[i]=$(basename ${j,,} | sed -r "s/-/_/g")
    f="${file[i]%.cpp}" 
    folder[i]=$(echo $f | sed -r "s/ikfast61_//g")
    #echo ${folder[i]} 
    #echo ${j%.cpp}
    #echo ${source[i]}
    #echo ${file[i]}  
    newFolder="$outPath${folder[i]}"
    #echo $newFolder
    cpPath="$newFolder/${file[i]}"
    #echo $cpPath
    mkdir "$newFolder/"
    cp "$template/CMakeLists.txt" "$newFolder/"
    cp "$template/ikfast.h" "$newFolder/"
    cp "$template/ikfast_pybind_abb_irb4600_40_255.cpp" "$newFolder/ikfast_pybind_${folder[i]}.cpp"
    cp ${source[i]} $cpPath
    #echo "s/abb_irb4600_40_255/${folder[i]}/"
    sed -i "s/ikfast0x10000049.Transform6D.0_1_2_3_4_5.cpp/${file[i]}/" "$newFolder/CMakeLists.txt"
    sed -i "s/abb_irb4600_40_255/${folder[i]}/" "$newFolder/CMakeLists.txt"
    sed -i "s/abb_irb4600_40_255/${folder[i]}/" "$newFolder/ikfast_pybind_${folder[i]}.cpp"
    #echo "${folder[i]}" "${outPath}CMakeLists.txt"
    #echo $(grep "${folder[i]} ${outPath}CMakeLists.txt")
    if grep  ${folder[i]} "${outPath}CMakeLists.txt"
    then
        echo "exists"
    else
        echo "add_subdirectory(${folder[i]})" >> "${outPath}CMakeLists.txt"
    fi
    i=$(( i + 1 ))
done
