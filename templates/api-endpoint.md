# {N}、{接口名称}

# 一、接口说明

{用一两句话简要描述该接口的用途与所处业务场景。}

# 二、请求地址

```bash
{/api/v1/xxx/xxx/{path_param}}
```

# 三、请求方式

```bash
{POST | GET | PUT | DELETE}
```

# 四、请求参数

## **1、Header参数**

| 名称  | 类型  | 必填  | 说明  | 示例  |
|-----|-----|-----|-----|-----|
| X-M-Sign / Authorization | str | 是   | 密钥，请参考接口鉴权说明 | Bearer xxx 或 Sign xxx |

## **2、路径参数**

### （1）说明

| 名称  | 类型  | 必填  | 说明  | 示例  |
|-----|-----|-----|-----|-----|
| {param_name} | str | 是   | {参数说明} | {示例值} |

### （2）示例

```bash
{/api/v1/xxx/xxx/example_value}
```

## **3、Query参数**

### （1）说明

| 名称  | 类型  | 必填  | 说明  | 示例  |
|-----|-----|-----|-----|-----|
| {param_name} | str | 否   | {参数说明} | {示例值} |

### （2）示例

```bash
{?key1=value1&key2=value2}
```

## **4、Body参数**

### （1）说明

| 名称  | 类型  | 必填  | 说明  | 示例  |
|-----|-----|-----|-----|-----|
| {field_name} | str | 是   | {字段说明} | {示例值} |

### （2）示例

```json
{
  "field_name": "example_value"
}
```

# 五、返回值

## 1、说明

| 名称  | 类型  | 说明  | 示例  |
|-----|-----|-----|-----|
| code | int | 成功 `10010`，失败 `10011` | 10010 |
| msg | str | 提示信息 | 操作成功 |
| request_id | str | 请求 ID | req-xxxxxxxxxxxx |
| data | object | 业务返回数据 | {} |

## **2、返回值示例**

```json
{
  "code": 10010,
  "msg": "操作成功",
  "request_id": "req-xxxxxxxxxxxx",
  "data": {}
}
```

# 六、请求示例

## 1、curl示例

```bash
curl --location --request POST 'http://127.0.0.1:10042/api/v1/xxx/xxx' \
--header 'Authorization: Bearer <your_token>' \
--header 'Content-Type: application/json' \
--data-raw '{
  "field_name": "example_value"
}'
```

# 七、相关说明/注意事项


1. {使用前的前置条件、依赖资源、约束}
2. {幂等性、错误码语义、与外部系统的关系}
3. {鉴权/权限/限流相关说明}
