#!/usr/bin/env python3
"""
Test ADB connection and basic commands
"""
import subprocess
import os
import time

def test_adb():
    print("🔍 Testing ADB Connection...")
    
    # Find ADB path
    sdk_paths = [
        os.path.expanduser("~/AppData/Local/Android/Sdk/platform-tools"),
        "C:/Users/Public/AppData/Local/Android/Sdk/platform-tools",
        "C:/Program Files/Android/Android Studio/Sdk/platform-tools"
    ]
    
    adb_path = None
    for path in sdk_paths:
        potential_path = os.path.join(path, "adb.exe")
        if os.path.exists(potential_path):
            adb_path = potential_path
            break
    
    if not adb_path:
        print("❌ ADB not found! Please install Android Studio first.")
        print("💡 Download from: https://developer.android.com/studio")
        return False
    
    print(f"✅ ADB found at: {adb_path}")
    
    # Test ADB version
    try:
        result = subprocess.run([adb_path, "version"], capture_output=True, text=True, timeout=10)
        print(f"✅ ADB Version: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ ADB version check failed: {e}")
        return False
    
    # Test ADB devices
    try:
        print("\n🔍 Checking for connected devices...")
        result = subprocess.run([adb_path, "devices"], capture_output=True, text=True, timeout=10)
        print(f"✅ ADB Devices Output:\n{result.stdout}")
        
        if "device" in result.stdout:
            print("✅ Device found and connected!")
        else:
            print("⚠️  No devices found. Please:")
            print("   1. Start Android Studio AVD")
            print("   2. Enable USB Debugging in Developer Options")
            print("   3. Wait for device to fully boot")
            return False
            
    except Exception as e:
        print(f"❌ ADB devices check failed: {e}")
        return False
    
    # Test basic input commands
    try:
        print("\n🧪 Testing basic input commands...")
        
        # Test tap command
        print("   Testing tap command...")
        result = subprocess.run([adb_path, "shell", "input", "tap", "100", "100"], 
                              capture_output=True, text=True, timeout=10)
        print("   ✅ Tap command executed")
        
        # Test back key
        print("   Testing back key...")
        result = subprocess.run([adb_path, "shell", "input", "keyevent", "KEYCODE_BACK"], 
                              capture_output=True, text=True, timeout=10)
        print("   ✅ Back key executed")
        
        # Test swipe command
        print("   Testing swipe command...")
        result = subprocess.run([adb_path, "shell", "input", "swipe", "100", "100", "200", "200", "500"], 
                              capture_output=True, text=True, timeout=10)
        print("   ✅ Swipe command executed")
        
    except Exception as e:
        print(f"❌ Input command test failed: {e}")
        return False
    
    print("\n🎉 ADB test completed successfully!")
    print("💡 You should see input actions in your Android emulator.")
    return True

if __name__ == "__main__":
    success = test_adb()
    if success:
        print("\n🎉 ADB is ready for automation!")
    else:
        print("\n💥 ADB setup failed. Please follow the installation guide.")
