# {模块编号}、{接口名称}

> [!INFO]
> **接口说明**：{用一两句话简要描述该接口的用途与所处业务场景。}

## 一、请求地址

```bash
{GET | POST | PUT | DELETE} /api/v1/xxx/xxx/{path_param}
```

## 二、请求参数

> [!INFO]
> 下列涉及的各个参数区块（Header, Path, Query, Body, FormData），**若当前接口中没有使用，可以直接省略（将对应分组区块整个删除）。**

### 1、Header 鉴权参数

| 名称  | 类型  | 必填  | 说明  | 示例  |
|-----|-----|-----|-----|-----|
| Authorization | str | 是   | 密钥，请参考接口鉴权说明 | Bearer xxx |

### 2、路径参数 (Path)

| 名称  | 类型  | 必填  | 说明  | 示例  |
|-----|-----|-----|-----|-----|
| {param_name} | str | 是   | {参数说明} | {示例值} |

### 3、查询参数 (Query)

| 名称  | 类型  | 必填  | 说明  | 示例  |
|-----|-----|-----|-----|-----|
| {param_name} | str | 否   | {参数说明} | {示例值} |

### 4、请求体参数 (Body)

| 名称  | 类型  | 必填  | 说明  | 示例  |
|-----|-----|-----|-----|-----|
| {field_name} | str | 是   | {字段说明} | {示例值} |

**JSON 请求示例**：
```json
{
  "field_name": "example_value"
}
```

### 5、表单参数 (FormData)

| 名称  | 类型  | 必填  | 说明  | 示例  |
|-----|-----|-----|-----|-----|
| {file_upload} | file | 是   | {选择要上传的文件二进制流} | binary |
| {extra_field} | str | 否   | {附加的文本字段} | {示例值} |

## 三、返回值

### 1、字段说明

| 名称  | 类型  | 说明  | 示例  |
|-----|-----|-----|-----|
| code | int | 成功 `10010`，失败 `10011` | 10010 |
| msg | str | 提示信息 | 操作成功 |
| request_id | str | 请求 ID | req-xxxxxxxxxxxx |
| data | object | 业务返回数据 | {} |

### 2、返回响应示例

```json
{
  "code": 10010,
  "msg": "操作成功",
  "request_id": "req-xxxxxxxxxxxx",
  "data": {}
}
```

## 四、请求示例

```bash
curl --location --request POST 'http://127.0.0.1:10042/api/v1/xxx/xxx' \
--header 'Authorization: Bearer <your_token>' \
--header 'Content-Type: application/json' \
--data-raw '{
  "field_name": "example_value"
}'
```

## 五、相关说明与注意事项

1. **调用前置**：{使用前的前置条件、依赖资源、约束}。
2. **幂等策略**：{幂等性、错误码语义、与外部系统的关系}。
3. **权限限流**：{鉴权、权限控制、限流规则}。
