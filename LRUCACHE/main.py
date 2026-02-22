class Node:
    def __init__(self,key:int,value:int):
        self.key=key
        self.value=value
        self.prev=None
        self.next=None

class LRUCache:
    def __init__(self,capacity:int):
        self.capacity=capacity
        self.cache=dict()
        self.head = Node(0,0)
        self.tail = Node(0,0)
        self.head.next=self.tail
        self.tail.prev=self.head
    def remove(self,node:Node):
        node.prev.next=node.next
        node.next.prev=node.prev
    def add_to_head(self,node:Node):
        node.next=self.head.next
        node.prev=self.head
        self.head.next.prev=node
        self.head.next=node
    def move_to_head(self,node:Node):
        self.remove(node)
        self.add_to_head(node)
    def get(self,key:int):
        if key in self.cache:
            node=self.cache[key]
            self.move_to_head(node)
            return node.value
        return -1
    def remove_lru(self):
        lru=self.tail.prev
        self.remove(lru)
        del self.cache[lru.key]
    def put(self,key:int,value:int):
        if key in self.cache:
            node=self.cache[key]
            node.value=value
            self.move_to_head(node)
        else:
            if len(self.cache)==self.capacity:
                self.remove_lru()
            new_node=Node(key,value)
            self.cache[key]=new_node
            self.add_to_head(new_node)