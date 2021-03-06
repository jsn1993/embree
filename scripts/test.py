#!/usr/bin/python

import sys
import os
import ctypes
import time
import datetime
import json
import socket
import subprocess

g_cdash = ""
g_config = {}
g_mode = "Experimental"
g_intensity = 2
g_debugMode = False
g_singleConfig = ""

def escape(str):
  str = str.replace("\\",r"\\")
  str = str.replace("\"",r"\"")
  return str

# detect platform
if sys.platform.startswith("win"):
  dash = '\\'
  SEM_FAILCRITICALERRORS = 0x0001
  SEM_NOGPFAULTERRORBOX  = 0x0002
  SEM_NOOPENFILEERRORBOX = 0x8000
  ctypes.windll.kernel32.SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX);
  OS = "windows"
elif sys.platform.startswith("cygwin"):
  dash = '/'
  SEM_FAILCRITICALERRORS = 0x0001
  SEM_NOGPFAULTERRORBOX  = 0x0002
  SEM_NOOPENFILEERRORBOX = 0x8000
  ctypes.cdll.kernel32.SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX);
  OS = "windows"
elif sys.platform.startswith("linux"):
  dash = '/'
  OS = "linux"
elif sys.platform.startswith("darwin"):
  dash = '/'
  OS = "macosx"
else:
  print("unknown platform: "+ sys.platform);
  sys.exit(1)

# runs all tests for specified host machine
def runConfig(config):

  conf = []  # CMake configuration
  env = []  # shell environment
  
  build = config["build"]
  conf.append("-D CMAKE_BUILD_TYPE="+build+"")
    
  if "memcheck" in config:
    conf.append("-D EMBREE_TESTING_MEMCHECK="+config["memcheck"]+"")

  if "sde" in config:
    conf.append("-D EMBREE_TESTING_SDE="+config["sde"]+"")

  if "addrsanitizer" in config:
    conf.append("-D EMBREE_ADDRESS_SANITIZER="+config["addrsanitizer"]+"")
    
  if "intensity" in config:
    conf.append("-D EMBREE_TESTING_INTENSITY="+config["intensity"])

  if "klocwork" in config:
    conf.append("-D EMBREE_TESTING_KLOCWORK="+config["klocwork"])

  if "package" in config:
    conf.append("-D EMBREE_STACK_PROTECTOR=ON")

  #if "package" in config and OS == 'linux': # we need up to date cmake for RPMs to work properly
  #  env.append("module load cmake")

  nas = "/NAS/packages/apps"

  compiler = config["compiler"]
  platform = config["platform"]
  ispc_ext = "-vs2013"
  if OS == "windows":
    ext = ""
    if platform == "x64":
      ext = " Win64"
    if (compiler == "V141"):
      conf.append("-G \"Visual Studio 15 2017"+ext+"\"")
      conf.append("-T \"V141\"")
      ispc_ext = "-vs2015"
    elif (compiler == "V140"):
      conf.append("-G \"Visual Studio 14 2015"+ext+"\"")
      conf.append("-T \"V140\"")
      ispc_ext = "-vs2015"
    elif (compiler == "V120"):
      conf.append("-G \"Visual Studio 12 2013"+ext+"\"")
      conf.append("-T \"V120\"")
    elif (compiler == "V110"):
      conf.append("-G \"Visual Studio 11 2012"+ext+"\"")
      conf.append("-T \"V110\"")
    elif (compiler == "ICC"):
      conf.append("-G \"Visual Studio 12 2013"+ext+"\"")
      conf.append("-T \"Intel C++ Compiler 17.0\"")
    elif (compiler == "ICC18"):
      conf.append("-G \"Visual Studio 12 2013"+ext+"\"")
      conf.append("-T \"Intel C++ Compiler 18.0\"")
    elif (compiler == "ICC17"):
      conf.append("-G \"Visual Studio 12 2013"+ext+"\"")
      conf.append("-T \"Intel C++ Compiler 17.0\"")
    elif (compiler == "ICC16"):
      conf.append("-G \"Visual Studio 12 2013"+ext+"\"")
      conf.append("-T \"Intel C++ Compiler 16.0\"")
    elif (compiler == "ICC15"):
      conf.append("-G \"Visual Studio 12 2013"+ext+"\"")
      conf.append("-T \"Intel C++ Compiler XE 15.0\"")
    elif (compiler == "CLANG"):
      conf.append("-G \"Visual Studio 12 2013"+ext+"\"")
      conf.append("-T \"LLVM-vs2013\"")
    else:
      raise ValueError('unknown compiler: ' + compiler + '')
    
  elif OS == "linux":
    if (compiler == "ICC18"):
      conf.append("-D CMAKE_CXX_COMPILER="+nas+"/intel/2018.0/bin/icpc -D CMAKE_C_COMPILER="+nas+"/intel/2018.0/bin/icc")
    elif (compiler == "ICC17"):
      conf.append("-D CMAKE_CXX_COMPILER="+nas+"/intel/2017.1/bin/icpc -D CMAKE_C_COMPILER="+nas+"/intel/2017.1/bin/icc")
    elif (compiler == "ICC16"):
      conf.append("-D CMAKE_CXX_COMPILER="+nas+"/intel/2016.3/bin/icpc -D CMAKE_C_COMPILER="+nas+"/intel/2016.3/bin/icc")
    elif (compiler == "ICC15"):
      conf.append("-D CMAKE_CXX_COMPILER="+nas+"/intel/2015.3/bin/icpc -D CMAKE_C_COMPILER="+nas+"/intel/2015.3/bin/icc")
    elif (compiler == "GCC"):
      conf.append("-D CMAKE_CXX_COMPILER=g++ -D CMAKE_C_COMPILER=gcc")
    elif (compiler == "CLANG5"):
      conf.append("-D CMAKE_CXX_COMPILER="+nas+"/clang/v5.0.0/bin/clang++ -D CMAKE_C_COMPILER="+nas+"/clang/v5.0.0/bin/clang")
    elif (compiler == "CLANG4"):
      conf.append("-D CMAKE_CXX_COMPILER="+nas+"/clang/v4.0.0/bin/clang++ -D CMAKE_C_COMPILER="+nas+"/clang/v4.0.0/bin/clang")
    elif (compiler == "CLANG"):
      conf.append("-D CMAKE_CXX_COMPILER=clang++ -D CMAKE_C_COMPILER=clang")
    else:
      raise ValueError('unknown compiler: ' + compiler + '')
    
  else:
    if (compiler == "ICC18"):
      conf.append("-D CMAKE_CXX_COMPILER=icpc -D CMAKE_C_COMPILER=icc")
      env.append("module load intel/2018")
    elif (compiler == "ICC17"):
      conf.append("-D CMAKE_CXX_COMPILER=icpc -D CMAKE_C_COMPILER=icc")
      env.append("module load intel/2017")
    elif (compiler == "ICC16"):
      conf.append("-D CMAKE_CXX_COMPILER=icpc -D CMAKE_C_COMPILER=icc")
      env.append("module load intel/2016")
    elif (compiler == "ICC15"):
      conf.append("-D CMAKE_CXX_COMPILER=icpc -D CMAKE_C_COMPILER=icc")
      env.append("module load intel/2015")
    elif (compiler == "GCC"):
      conf.append("-D CMAKE_CXX_COMPILER=g++ -D CMAKE_C_COMPILER=gcc")
    elif (compiler == "CLANG"):
      conf.append("-D CMAKE_CXX_COMPILER=clang++ -D CMAKE_C_COMPILER=clang")
    else:
      raise ValueError('unknown compiler: ' + compiler + '')

  ispc_compiler = config["ispc"]
  if ispc_compiler.startswith("ispc"):
    ispc_version = ispc_compiler[4:]
    if ispc_version != "":
      if OS == "linux":
        conf.append("-D EMBREE_ISPC_EXECUTABLE=/NAS/packages/apps/ispc/"+ispc_version+"-linux/ispc")
      elif OS == "macosx":
        conf.append("-D EMBREE_ISPC_EXECUTABLE=/Network/nfs/NAS/packages/apps/ispc/"+ispc_version+"-osx/ispc")
      elif OS == "windows":
        conf.append("-D EMBREE_ISPC_EXECUTABLE=\\\\sdvis-nas\\NAS\\packages\\apps\\ispc\\"+ispc_version+"-windows"+ispc_ext+"\\ispc.exe")
      else:
        sys.stderr.write("unknown operating system "+OS)
        sys.exit(1)
  else:
    raise ValueError('unknown ISPC compiler: ' + ispccompiler + '')
    
  isa = config["isa"]
  if type(isa) == str:
    conf.append("-D EMBREE_MAX_ISA="+isa+"")
  else:
    conf.append("-D EMBREE_MAX_ISA=NONE")
    if "SSE2"      in isa: conf.append("-D EMBREE_ISA_SSE2=ON")
    else                 : conf.append("-D EMBREE_ISA_SSE2=OFF")
    if "SSE42"     in isa: conf.append("-D EMBREE_ISA_SSE42=ON")
    else                 : conf.append("-D EMBREE_ISA_SSE42=OFF")
    if "AVX"       in isa: conf.append("-D EMBREE_ISA_AVX=ON")
    else                 : conf.append("-D EMBREE_ISA_AVX=OFF")
    if "AVX2"      in isa: conf.append("-D EMBREE_ISA_AVX2=ON")
    else                 : conf.append("-D EMBREE_ISA_AVX2=OFF")
    if "AVX512KNL" in isa: conf.append("-D EMBREE_ISA_AVX512KNL=ON")
    else                 : conf.append("-D EMBREE_ISA_AVX512KNL=OFF")
    if "AVX512SKX" in isa: conf.append("-D EMBREE_ISA_AVX512SKX=ON")
    else                 : conf.append("-D EMBREE_ISA_AVX512SKX=OFF")

  if "tasking" in config:
    tasking  = config["tasking"]
    if tasking == "INT":
      conf.append("-D EMBREE_TASKING_SYSTEM=INTERNAL")
    elif tasking == "PPL":
      conf.append("-D EMBREE_TASKING_SYSTEM=PPL")
    elif tasking.startswith("TBB"):
      conf.append("-D EMBREE_TASKING_SYSTEM=TBB")

      if OS == "linux":
        if tasking == "TBB2017":
          conf.append("-D EMBREE_TBB_ROOT=/NAS/packages/apps/tbb/tbb-2017-linux")
        elif tasking == "TBB":
          conf.append("-D EMBREE_TBB_ROOT=/usr")
        else:
          raise ValueError('unknown tasking system: ' + tasking + '')
      
      elif OS == "macosx":
        if tasking == "TBB2017":
          conf.append("-D EMBREE_TBB_ROOT=/Network/nfs/NAS/packages/apps/tbb/tbb-2017-osx")
        elif tasking == "TBB":
          conf.append("-D EMBREE_TBB_ROOT=/opt/local")
        else:
          raise ValueError('unknown tasking system: ' + tasking + '')
      
      elif OS == "windows":
        if tasking == "TBB2017": 
          tbb_path = "\\\\sdvis-nas\\NAS\\packages\\apps\\tbb\\tbb-2017-windows"
          conf.append("-D EMBREE_TBB_ROOT="+tbb_path)
        else:
          raise ValueError('unknown tasking system: ' + tasking + '')

        if platform == "x64":
          env.append("set PATH="+tbb_path+"\\bin\\intel64\\vc12;%PATH%")
        else:
          env.append("set PATH="+tbb_path+"\\bin\\ia32\\vc12;%PATH%")

      else:
        sys.stderr.write("unknown operating system "+OS)
        sys.exit(1)
        
    else:
      raise ValueError('unknown tasking system: ' + tasking)      
    
  if "ISPC_SUPPORT" in config:
    conf.append("-D EMBREE_ISPC_SUPPORT="+config["ISPC_SUPPORT"])
  if "STATIC_LIB" in config:
    conf.append("-D EMBREE_STATIC_LIB="+config["STATIC_LIB"])
  if "TUTORIALS" in config:
    conf.append("-D EMBREE_TUTORIALS="+config["TUTORIALS"])
  if "BACKFACE_CULLING" in config:
    conf.append("-D EMBREE_BACKFACE_CULLING="+config["BACKFACE_CULLING"])
  if "IGNORE_INVALID_RAYS" in config:
    conf.append("-D EMBREE_IGNORE_INVALID_RAYS="+config["IGNORE_INVALID_RAYS"])
  if "INTERSECTION_FILTER" in config:
    conf.append("-D EMBREE_INTERSECTION_FILTER="+config["INTERSECTION_FILTER"])
  if "RAY_MASK" in config:
    conf.append("-D EMBREE_RAY_MASK="+config["RAY_MASK"])
  if "RAY_PACKETS" in config:
    conf.append("-D EMBREE_RAY_PACKETS="+config["RAY_PACKETS"])
  if "STAT_COUNTERS" in config:
    conf.append("-D EMBREE_STAT_COUNTERS="+config["STAT_COUNTERS"])
  if "TRIS" in config:
    conf.append("-D EMBREE_GEOMETRY_TRIANGLES="+config["TRIS"])
  if "QUADS" in config:
    conf.append("-D EMBREE_GEOMETRY_QUADS="+config["QUADS"])
  if "LINES" in config:
    conf.append("-D EMBREE_GEOMETRY_LINES="+config["LINES"])
  if "HAIR" in config:
    conf.append("-D EMBREE_GEOMETRY_HAIR="+config["HAIR"])
  if "SUBDIV" in config:
    conf.append("-D EMBREE_GEOMETRY_SUBDIV="+config["SUBDIV"])
  if "USERGEOM" in config:
    conf.append("-D EMBREE_GEOMETRY_USER="+config["USERGEOM"])

  if "package" in config:
    conf.append("-D EMBREE_TESTING_PACKAGE=ON")
    conf.append("-D EMBREE_TUTORIALS_IMAGE_MAGICK=OFF")
    conf.append("-D EMBREE_TUTORIALS_LIBJPEG=OFF")
    conf.append("-D EMBREE_TUTORIALS_LIBPNG=OFF")
    if OS == "linux" and config["package"] == "ZIP":
      conf.append("-D EMBREE_INSTALL_DEPENDENCIES=ON")
      conf.append("-D EMBREE_ZIP_MODE=ON")
      conf.append("-D CMAKE_SKIP_INSTALL_RPATH=ON")
      conf.append("-D CMAKE_INSTALL_INCLUDEDIR=include")
      conf.append("-D CMAKE_INSTALL_LIBDIR=lib")
      conf.append("-D CMAKE_INSTALL_DOCDIR=doc")
      conf.append("-D CMAKE_INSTALL_BINDIR=bin")
    elif OS == "linux" and config["package"] == "RPM":
      conf.append("-D EMBREE_INSTALL_DEPENDENCIES=OFF")
      conf.append("-D EMBREE_ZIP_MODE=OFF")
      conf.append("-D CMAKE_SKIP_INSTALL_RPATH=OFF")
      conf.append("-D CMAKE_INSTALL_PREFIX=/usr")
      conf.append("-D EMBREE_TBB_ROOT=/usr")
    elif OS == "macosx" and config["package"] == "ZIP":
      conf.append("-D EMBREE_INSTALL_DEPENDENCIES=ON")
      conf.append("-D EMBREE_ZIP_MODE=ON")
      conf.append("-D CMAKE_SKIP_INSTALL_RPATH=ON")
      conf.append("-D CMAKE_MACOSX_RPATH=ON")
      conf.append("-D CMAKE_INSTALL_INCLUDEDIR=include")
      conf.append("-D CMAKE_INSTALL_LIBDIR=lib")
      conf.append("-D CMAKE_INSTALL_DOCDIR=doc")
      conf.append("-D CMAKE_INSTALL_BINDIR=bin")
    elif OS == "macosx" and config["package"] == "PKG":
      conf.append("-D EMBREE_INSTALL_DEPENDENCIES=OFF")
      conf.append("-D EMBREE_ZIP_MODE=OFF")
      conf.append("-D CMAKE_SKIP_INSTALL_RPATH=OFF")
      conf.append("-D CMAKE_INSTALL_PREFIX=/opt/local")
      conf.append("-D CMAKE_INSTALL_INCLUDEDIR=include")
      conf.append("-D CMAKE_INSTALL_LIBDIR=lib")
      conf.append("-D CMAKE_INSTALL_DOCDIR=../../Applications/Embree2/doc")
      conf.append("-D CMAKE_INSTALL_BINDIR=../../Applications/Embree2/bin")
      conf.append("-D EMBREE_TBB_ROOT=/opt/local")
    elif OS == "windows" and config["package"] == "ZIP":
      conf.append("-D EMBREE_INSTALL_DEPENDENCIES=ON")
      conf.append("-D EMBREE_ZIP_MODE=ON")
      conf.append("-D CMAKE_INSTALL_INCLUDEDIR=include")
      conf.append("-D CMAKE_INSTALL_LIBDIR=lib")
      conf.append("-D CMAKE_INSTALL_DATAROOTDIR=")
      conf.append("-D CMAKE_INSTALL_DOCDIR=doc")
      conf.append("-D CMAKE_INSTALL_BINDIR=bin")
    elif OS == "windows" and config["package"] == "MSI":
      conf.append("-D EMBREE_INSTALL_DEPENDENCIES=ON")
      conf.append("-D EMBREE_ZIP_MODE=OFF")
      conf.append("-D CMAKE_INSTALL_INCLUDEDIR=include")
      conf.append("-D CMAKE_INSTALL_LIBDIR=lib")
      conf.append("-D CMAKE_INSTALL_DATAROOTDIR=")
      conf.append("-D CMAKE_INSTALL_DOCDIR=doc")
      conf.append("-D CMAKE_INSTALL_BINDIR=bin")
    else:
      sys.stderr.write("unknown package mode: "+OS+":"+config["package"])
      sys.exit(1)

  ctest =  "ctest -VV -S scripts/test.cmake"
  if g_cdash != "": ctest += " -D CTEST_DROP_SITE="+g_cdash
  ctest += " -D EMBREE_TESTING_INTENSITY="+str(g_intensity)
  ctest += " -D CTEST_CONFIGURATION_TYPE=\""+build+"\""
  ctest += " -D CTEST_BUILD_OPTIONS=\"" + escape(" ".join(conf))+"\""
  if g_debugMode:
    for e in env: print('    '+e)
    print('    '+ctest+'\n')
  else:
    cmd = ""
    for e in env: cmd += e + " && "
    cmd += ctest+"\n"
    if OS == "windows":
      try:
        subprocess.check_call(cmd, stderr=subprocess.STDOUT, shell=True)
      except subprocess.CalledProcessError, e:
        sys.stderr.write("windows test invokation failed with return code "+str(e.returncode))
        sys.exit(1)
    else:
      # need to use bash shell as we configured environment modules only for bash
      process = subprocess.Popen(['bash','-l'], stdin=subprocess.PIPE)
      process.communicate(input=cmd.encode("utf-8"))
      if process.returncode != 0:
        sys.stderr.write("test invokation failed with return code "+str(process.returncode))
        sys.exit(1)
    
def parseCommandLine(argv):
  global g_cdash
  global g_docker
  global g_config
  global g_mode
  global g_intensity
  global g_debugMode
  if len(argv) == 0:
    return;
  elif len(argv)>=2 and argv[0] == "--cdash":
    g_cdash = argv[1]
    parseCommandLine(argv[2:len(argv)])
  elif len(argv)>=2 and argv[0] == "--mode":
    g_mode = argv[1]
  elif len(argv)>=1 and argv[0] == "--debug":
    g_debugMode = True
    parseCommandLine(argv[1:len(argv)])
  elif len(argv)>=1 and argv[0] == "--help":
    printUsage()
    return;
  elif ':' in argv[0]:
    p = argv[0].split(":")
    if p[0] == "intensity":
      g_intensity = int(p[1])
    if p[1].startswith('[') and p[1].endswith(']'):
      g_config[p[0]] = p[1][1:-1].split(',')
    else:
      g_config[p[0]] = p[1]
    parseCommandLine(argv[1:len(argv)])
  else:
    sys.stderr.write("unknown command line option: "+argv[0])
    sys.exit(1)
      
parseCommandLine(sys.argv[1:len(sys.argv)])
runConfig(g_config)
