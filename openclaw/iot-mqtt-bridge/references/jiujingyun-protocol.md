---
name: jiujingyun-protocol
description: 九井云 IoT 设备 MQTT 协议参考
---

# 九井云设备协议参考

源自 `docs/reference/1.jiujingyun.md`

## MQTT 连接参数

| 参数 | 值 |
|------|-----|
| Broker IP | IOT平台服务器IP |
| 端口 | 1883 |
| ClientID | 设备SN号 |
| Username/Password | 见平台配置 |

## Topic 格式

### 属性上报（设备→平台）
```
/system/{productKey}/{deviceKey}/thing/property/post
```

### 服务命令（平台→设备）
```
/system/{productKey}/{deviceKey}/thing/service/{serviceName}
```

### 服务回复（设备→平台）
```
/system/{productKey}/{deviceKey}/thing/service/{serviceName}_reply
```

## 服务命令列表

| 服务名 | 功能 | 关键参数 |
|--------|------|----------|
| SetDeviceName | 修改设备名称 | DeviceName |
| SetNTPConfig | NTP配置 | NtpSwitch, NtpServer1, NtpServer2 |
| SetUserInfo | 用户名密码修改 | OldUserName, NewUserName, OldUserPassword, NewUserPassword |
| DeviceReboot | 定时重启 | Rule(0按月/1按周/2按天/3关闭), Day, Week, Hour, Minutes |
| WANPPPOEConfig | WAN PPPOE | Switch, GatewayHop, DNS, UserName, Password, Name |
| WANSTATICConfig | WAN静态IP | Switch, IPAddress, Mask, Gateway, DNS |
| WANDHCPConfig | WAN DHCP | Switch, DNS |
| WANPriority | WAN优先级 | Interface(nrWan/nrWan2/wlan5G/wiredWan1等), Priority |
| LANConfig | LAN配置 | Server, Mask, DHCPSwitch, DHCPStartIp, DHCPEndIp, LeaseTime, DNS |
| MobileNetworkConfig | 移动网络 | Id(1-4), Switch, APN, AuthMethod, UserName, Password, DataRoamingSwitch |
| FiveGLANConfig | 5GLAN配置 | ID(1-2), Switch, APN, AuthMethod |
| LockScreenLockCommunity | 锁频锁小区 | Function(0关闭/1锁定频点/2锁定小区/3锁定Band), ID, Band, FrequencyPoint |
| SIMConfig | SIM配置 | MainCardSelect, PINCard1, PUKCard1, BindSIMCard1, WantBindSIMCard1 |
| HotStandby | 双机热备份 | Switch, SerialNumber, Role(MASTER/BACKUP), VRID, HeartbeatInterval |
| VLANConfig | VLAN配置 | Action(edit/delete), VLANID, Port0-5, LAN1, LAN2, CPU |
| NATForwardingConfig | NAT转发 | Action(add/deleteAll), Protocol(0TCP/1UDP/2TCP+UDP), ExternalPort, InternalIP, InternalPort |
| DMZ | DMZ配置 | Switch, InternalIp |
| RestoreFactorySettings | 恢复出厂 | 无参数 |
| RebootDevice | 重启设备 | 无参数 |
| SetPING | Ping检测 | Action(1开始/0停止), Address |

## 命令下发示例

```bash
# 修改设备名称
adapter.sh send_command my-product test-device-001 SetDeviceName '{"DeviceName":"MyRouter"}'

# WAN优先级配置
adapter.sh send_command my-product test-device-001 WANPriority '{"Interface":"nrWan","Priority":1}'

# 重启设备
adapter.sh send_command my-product test-device-001 RebootDevice '{}'
```

## 设备回复格式

```json
{
  "code": 200,
  "data": {
    "Result": "OK",
    "Code": "0",
    "Time": "1234567890"
  },
  "id": "对应命令id",
  "message": "success",
  "version": "1.0"
}
```

## 常用设备标识

在调用命令时需要知道 `productKey` 和 `deviceKey`，这些由九井云平台分配。可在设备配置或平台界面获取。

测试环境示例值：
- productKey: `test-product`
- deviceKey: `test-device-001`