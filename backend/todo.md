# ActionEngine Backend Todo (Mar 17)

- [ ] Test terminal use. I tested the tool in isolation, but I haven't tested if the model can call the tool

- [ ] Come up with a better pattern for handling messages. We just continually append to a giant array for every single message, so each node gets the system prompt of all the subsequent nodes which I think is confusing the model and also just adding excess, useless tokens.

- [ ] Getting this for previous actions. Should show the action and args

```markdown
The agent before you performed these actions:

2: None(None)

5: planning(None)

6: None(None)
```

- [ ] Resolve an issue where instead of clicking on element_ids, it tries to click like

```json
{
  "action": "click",
  "url": "https://en.wikipedia.org/wiki/Main_Page"
}
```

- [ ] Trying to figure out why it refuses to terminate execution. Both the planning and executor nodes have access to a terminate function, but it just never wants to call it.

- [ ] Refactor where files are located, move things to logical places
