# good.md -- every checkable snippet here verifies clean.

```python
def add(a, b):
    return a + b
```

```json
{"ok": true, "count": 2}
```

```javascript
const x = add(2, 3);
console.log(x);
```

```console
$ python -c "print(1)"
1
$(this output line is NOT a command -- never verified
```

```go
package main

func main() {}
```

```text
just prose in a box
```

```python skip
def broken(:  # the skip marker opts this block out
    pass
```
