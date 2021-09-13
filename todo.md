# Solutions
## Attribute如何支持？
### Unresolved Attribute

### Attributed的引用(Set, Call)的支持
在当前作用域如果能得到Variable Entity的EntType，则：

1. 如果receiver为AnyType，建立全局的Referenced Attribute，直接对此Attribute建立Use/Set，最后再对dep_db进行一次约束求解即可
2. 如果receiver为ClassType，否则直接建立对相应Class的Attribute的Use/Set
3. 其他情况，建立Unresolved Attribute


### class def 的environment问题
