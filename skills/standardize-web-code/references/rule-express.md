# Express 规则

- Router 组合 URL 与中间件；Controller/Handler 转换 HTTP；Service 实现业务用例；Repository/Data Access 访问持久层。Service 不依赖 `req`/`res`。
- 每个 handler 的执行路径只能响应一次：返回响应、调用 `next` 或抛错。异步错误按项目统一方式交给错误处理中间件，不复制无意义 catch 模板。
- 在边界验证并规范化 params、query 和 body；不要把 `req.body` 直接交给持久层。认证中间件解析身份，授权规则仍在明确的策略或业务用例中执行。
- 错误处理中间件集中处理状态码、公开消息、日志和内部错误映射。中间件顺序是行为契约，调整后运行受影响集成测试。
