"""Boilerplate service to provide clean runnable starter code templates across multiple languages
(Python, JavaScript, Java, C++, Go) for technical interview questions.
Adheres strictly to minimal comments: only 'Type your code here' is included.
"""

from typing import Optional, Dict
from backend.services.question_loader import QuestionItem

# Map question_id -> { language: code_string }
# Clean, minimal runnable boilerplates with only 'Type your code here'
BOILERPLATES: Dict[str, Dict[str, str]] = {
    # -------------------------------------------------------------
    # arr-1: Two Sum
    # -------------------------------------------------------------
    "arr-1": {
        "python": '''class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        # Type your code here
        pass

if __name__ == "__main__":
    sol = Solution()
    print("Result:", sol.twoSum([2, 7, 11, 15], 9))
''',
        "javascript": '''function twoSum(nums, target) {
  // Type your code here
}

console.log("Result:", twoSum([2, 7, 11, 15], 9));
''',
        "java": '''import java.util.*;

public class Solution {
    public int[] twoSum(int[] nums, int target) {
        // Type your code here
        return new int[]{};
    }

    public static void main(String[] args) {
        Solution sol = new Solution();
        System.out.println("Result: " + Arrays.toString(sol.twoSum(new int[]{2, 7, 11, 15}, 9)));
    }
}
''',
        "cpp": '''#include <iostream>
#include <vector>

class Solution {
public:
    std::vector<int> twoSum(std::vector<int>& nums, int target) {
        // Type your code here
        return {};
    }
};

int main() {
    Solution sol;
    std::vector<int> nums = {2, 7, 11, 15};
    auto res = sol.twoSum(nums, 9);
    std::cout << "Result: [" << res[0] << ", " << res[1] << "]" << std::endl;
    return 0;
}
''',
        "go": '''package main

import "fmt"

func twoSum(nums []int, target int) []int {
    // Type your code here
    return nil
}

func main() {
    nums := []int{2, 7, 11, 15}
    fmt.Println("Result:", twoSum(nums, 9))
}
'''
    },

    # -------------------------------------------------------------
    # arr-2: Maximum Subarray (Kadane's)
    # -------------------------------------------------------------
    "arr-2": {
        "python": '''class Solution:
    def maxSubArray(self, nums: list[int]) -> int:
        # Type your code here
        pass

if __name__ == "__main__":
    sol = Solution()
    print("Max Subarray:", sol.maxSubArray([-2, 1, -3, 4, -1, 2, 1, -5, 4]))
''',
        "javascript": '''function maxSubArray(nums) {
  // Type your code here
}

console.log("Max Subarray:", maxSubArray([-2, 1, -3, 4, -1, 2, 1, -5, 4]));
''',
        "java": '''public class Solution {
    public int maxSubArray(int[] nums) {
        // Type your code here
        return 0;
    }

    public static void main(String[] args) {
        Solution sol = new Solution();
        System.out.println("Max Subarray: " + sol.maxSubArray(new int[]{-2, 1, -3, 4, -1, 2, 1, -5, 4}));
    }
}
''',
        "cpp": '''#include <iostream>
#include <vector>

class Solution {
public:
    int maxSubArray(std::vector<int>& nums) {
        // Type your code here
        return 0;
    }
};

int main() {
    Solution sol;
    std::vector<int> nums = {-2, 1, -3, 4, -1, 2, 1, -5, 4};
    std::cout << "Max Subarray: " << sol.maxSubArray(nums) << std::endl;
    return 0;
}
''',
        "go": '''package main

import "fmt"

func maxSubArray(nums []int) int {
    // Type your code here
    return 0
}

func main() {
    nums := []int{-2, 1, -3, 4, -1, 2, 1, -5, 4}
    fmt.Println("Max Subarray:", maxSubArray(nums))
}
'''
    },

    # -------------------------------------------------------------
    # arr-3: Sort Colors (Dutch National Flag)
    # -------------------------------------------------------------
    "arr-3": {
        "python": '''class Solution:
    def sortColors(self, nums: list[int]) -> None:
        # Type your code here
        pass

if __name__ == "__main__":
    sol = Solution()
    nums = [2, 0, 2, 1, 1, 0]
    sol.sortColors(nums)
    print("Sorted Colors:", nums)
''',
        "javascript": '''function sortColors(nums) {
  // Type your code here
}

const arr = [2, 0, 2, 1, 1, 0];
sortColors(arr);
console.log("Sorted Colors:", arr);
''',
        "java": '''import java.util.*;

public class Solution {
    public void sortColors(int[] nums) {
        // Type your code here
    }

    public static void main(String[] args) {
        Solution sol = new Solution();
        int[] nums = {2, 0, 2, 1, 1, 0};
        sol.sortColors(nums);
        System.out.println("Sorted Colors: " + Arrays.toString(nums));
    }
}
''',
        "cpp": '''#include <iostream>
#include <vector>

class Solution {
public:
    void sortColors(std::vector<int>& nums) {
        // Type your code here
    }
};

int main() {
    Solution sol;
    std::vector<int> nums = {2, 0, 2, 1, 1, 0};
    sol.sortColors(nums);
    std::cout << "Sorted Colors: [";
    for (int n : nums) std::cout << n << " ";
    std::cout << "]" << std::endl;
    return 0;
}
''',
        "go": '''package main

import "fmt"

func sortColors(nums []int) {
    // Type your code here
}

func main() {
    nums := []int{2, 0, 2, 1, 1, 0}
    sortColors(nums)
    fmt.Println("Sorted Colors:", nums)
}
'''
    },

    # -------------------------------------------------------------
    # bs-1: Search in Rotated Sorted Array
    # -------------------------------------------------------------
    "bs-1": {
        "python": '''class Solution:
    def search(self, nums: list[int], target: int) -> int:
        # Type your code here
        pass

if __name__ == "__main__":
    sol = Solution()
    print("Search Index:", sol.search([4, 5, 6, 7, 0, 1, 2], 0))
''',
        "javascript": '''function search(nums, target) {
  // Type your code here
  return -1;
}

console.log("Index:", search([4, 5, 6, 7, 0, 1, 2], 0));
''',
        "java": '''public class Solution {
    public int search(int[] nums, int target) {
        // Type your code here
        return -1;
    }

    public static void main(String[] args) {
        Solution sol = new Solution();
        System.out.println("Index: " + sol.search(new int[]{4, 5, 6, 7, 0, 1, 2}, 0));
    }
}
''',
        "cpp": '''#include <iostream>
#include <vector>

class Solution {
public:
    int search(std::vector<int>& nums, int target) {
        // Type your code here
        return -1;
    }
};

int main() {
    Solution sol;
    std::vector<int> nums = {4, 5, 6, 7, 0, 1, 2};
    std::cout << "Index: " << sol.search(nums, 0) << std::endl;
    return 0;
}
''',
        "go": '''package main

import "fmt"

func search(nums []int, target int) int {
    // Type your code here
    return -1
}

func main() {
    nums := []int{4, 5, 6, 7, 0, 1, 2}
    fmt.Println("Index:", search(nums, 0))
}
'''
    },

    # -------------------------------------------------------------
    # bs-2: Allocate Minimum Pages / Book Allocation
    # -------------------------------------------------------------
    "bs-2": {
        "python": '''class Solution:
    def findPages(self, pages: list[int], k: int) -> int:
        # Type your code here
        pass

if __name__ == "__main__":
    sol = Solution()
    print("Min Pages Allocated:", sol.findPages([12, 34, 67, 90], 2))
''',
        "javascript": '''function findPages(pages, k) {
  // Type your code here
  return 0;
}

console.log("Min Pages:", findPages([12, 34, 67, 90], 2));
''',
        "java": '''public class Solution {
    public int findPages(int[] pages, int k) {
        // Type your code here
        return 0;
    }

    public static void main(String[] args) {
        Solution sol = new Solution();
        System.out.println("Min Pages: " + sol.findPages(new int[]{12, 34, 67, 90}, 2));
    }
}
''',
        "cpp": '''#include <iostream>
#include <vector>

class Solution {
public:
    int findPages(std::vector<int>& pages, int k) {
        // Type your code here
        return 0;
    }
};

int main() {
    Solution sol;
    std::vector<int> pages = {12, 34, 67, 90};
    std::cout << "Min Pages: " << sol.findPages(pages, 2) << std::endl;
    return 0;
}
''',
        "go": '''package main

import "fmt"

func findPages(pages []int, k int) int {
    // Type your code here
    return 0
}

func main() {
    pages := []int{12, 34, 67, 90}
    fmt.Println("Min Pages:", findPages(pages, 2))
}
'''
    },

    # -------------------------------------------------------------
    # ll-1: Reverse Linked List
    # -------------------------------------------------------------
    "ll-1": {
        "python": '''class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class Solution:
    def reverseList(self, head: ListNode | None) -> ListNode | None:
        # Type your code here
        pass

def print_list(node):
    res = []
    while node:
        res.append(str(node.val))
        node = node.next
    print(" -> ".join(res))

if __name__ == "__main__":
    head = ListNode(1, ListNode(2, ListNode(3, ListNode(4, ListNode(5)))))
    sol = Solution()
    print_list(sol.reverseList(head))
''',
        "javascript": '''class ListNode {
  constructor(val = 0, next = null) {
    this.val = val;
    this.next = next;
  }
}

function reverseList(head) {
  // Type your code here
}

const head = new ListNode(1, new ListNode(2, new ListNode(3)));
console.log("Reversed:", reverseList(head));
''',
        "java": '''class ListNode {
    int val;
    ListNode next;
    ListNode(int val) { this.val = val; }
    ListNode(int val, ListNode next) { this.val = val; this.next = next; }
}

public class Solution {
    public ListNode reverseList(ListNode head) {
        // Type your code here
        return null;
    }

    public static void main(String[] args) {
        ListNode head = new ListNode(1, new ListNode(2, new ListNode(3)));
        Solution sol = new Solution();
        ListNode rev = sol.reverseList(head);
    }
}
''',
        "cpp": '''#include <iostream>

struct ListNode {
    int val;
    ListNode *next;
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode *n) : val(x), next(n) {}
};

class Solution {
public:
    ListNode* reverseList(ListNode* head) {
        // Type your code here
        return nullptr;
    }
};

int main() {
    ListNode* head = new ListNode(1, new ListNode(2, new ListNode(3)));
    Solution sol;
    ListNode* rev = sol.reverseList(head);
    return 0;
}
''',
        "go": '''package main

import "fmt"

type ListNode struct {
    Val  int
    Next *ListNode
}

func reverseList(head *ListNode) *ListNode {
    // Type your code here
    return nil
}

func main() {
    head := &ListNode{Val: 1, Next: &ListNode{Val: 2, Next: &ListNode{Val: 3}}}
    fmt.Println("Reversed:", reverseList(head))
}
'''
    },

    # -------------------------------------------------------------
    # ll-2: Linked List Cycle II
    # -------------------------------------------------------------
    "ll-2": {
        "python": '''class ListNode:
    def __init__(self, x):
        self.val = x
        self.next = None

class Solution:
    def detectCycle(self, head: ListNode | None) -> ListNode | None:
        # Type your code here
        pass

if __name__ == "__main__":
    sol = Solution()
    node1 = ListNode(3)
    node2 = ListNode(2)
    node1.next = node2
    node2.next = node1
    print("Cycle detected at node val:", sol.detectCycle(node1).val)
''',
        "javascript": '''class ListNode {
  constructor(x) {
    this.val = x;
    this.next = null;
  }
}

function detectCycle(head) {
  // Type your code here
  return null;
}

const n1 = new ListNode(3);
const n2 = new ListNode(2);
n1.next = n2;
n2.next = n1;
console.log("Cycle at:", detectCycle(n1)?.val);
''',
        "java": '''class ListNode {
    int val;
    ListNode next;
    ListNode(int x) { val = x; next = null; }
}

public class Solution {
    public ListNode detectCycle(ListNode head) {
        // Type your code here
        return null;
    }
}
''',
        "cpp": '''struct ListNode {
    int val;
    ListNode *next;
    ListNode(int x) : val(x), next(nullptr) {}
};

class Solution {
public:
    ListNode *detectCycle(ListNode *head) {
        // Type your code here
        return nullptr;
    }
};
''',
        "go": '''package main

type ListNode struct {
    Val  int
    Next *ListNode
}

func detectCycle(head *ListNode) *ListNode {
    // Type your code here
    return nil
}
'''
    },

    # -------------------------------------------------------------
    # sw-1: Longest Substring Without Repeating Characters
    # -------------------------------------------------------------
    "sw-1": {
        "python": '''class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        # Type your code here
        pass

if __name__ == "__main__":
    sol = Solution()
    print("Length:", sol.lengthOfLongestSubstring("abcabcbb"))
''',
        "javascript": '''function lengthOfLongestSubstring(s) {
  // Type your code here
  return 0;
}

console.log("Length:", lengthOfLongestSubstring("abcabcbb"));
''',
        "java": '''public class Solution {
    public int lengthOfLongestSubstring(String s) {
        // Type your code here
        return 0;
    }

    public static void main(String[] args) {
        Solution sol = new Solution();
        System.out.println("Length: " + sol.lengthOfLongestSubstring("abcabcbb"));
    }
}
''',
        "cpp": '''#include <iostream>
#include <string>

class Solution {
public:
    int lengthOfLongestSubstring(std::string s) {
        // Type your code here
        return 0;
    }
};

int main() {
    Solution sol;
    std::cout << "Length: " << sol.lengthOfLongestSubstring("abcabcbb") << std::endl;
    return 0;
}
''',
        "go": '''package main

import "fmt"

func lengthOfLongestSubstring(s string) int {
    // Type your code here
    return 0
}

func main() {
    fmt.Println("Length:", lengthOfLongestSubstring("abcabcbb"))
}
'''
    },

    # -------------------------------------------------------------
    # tree-1: Binary Tree Level Order Traversal
    # -------------------------------------------------------------
    "tree-1": {
        "python": '''class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

class Solution:
    def levelOrder(self, root: TreeNode | None) -> list[list[int]]:
        # Type your code here
        pass

if __name__ == "__main__":
    root = TreeNode(3, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))
    sol = Solution()
    print("Level Order:", sol.levelOrder(root))
''',
        "javascript": '''class TreeNode {
  constructor(val = 0, left = null, right = null) {
    this.val = val;
    this.left = left;
    this.right = right;
  }
}

function levelOrder(root) {
  // Type your code here
  return [];
}
''',
        "java": '''import java.util.*;

class TreeNode {
    int val;
    TreeNode left, right;
    TreeNode(int x) { val = x; }
}

public class Solution {
    public List<List<Integer>> levelOrder(TreeNode root) {
        // Type your code here
        return new ArrayList<>();
    }
}
''',
        "cpp": '''#include <iostream>
#include <vector>

struct TreeNode {
    int val;
    TreeNode *left;
    TreeNode *right;
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

class Solution {
public:
    std::vector<std::vector<int>> levelOrder(TreeNode* root) {
        // Type your code here
        return {};
    }
};
''',
        "go": '''package main

type TreeNode struct {
    Val   int
    Left  *TreeNode
    Right *TreeNode
}

func levelOrder(root *TreeNode) [][]int {
    // Type your code here
    return nil
}
'''
    },

    # -------------------------------------------------------------
    # graph-1: Course Schedule
    # -------------------------------------------------------------
    "graph-1": {
        "python": '''class Solution:
    def canFinish(self, numCourses: int, prerequisites: list[list[int]]) -> bool:
        # Type your code here
        pass

if __name__ == "__main__":
    sol = Solution()
    print("Can finish:", sol.canFinish(2, [[1, 0]]))
''',
        "javascript": '''function canFinish(numCourses, prerequisites) {
  // Type your code here
  return true;
}

console.log("Can finish:", canFinish(2, [[1, 0]]));
''',
        "java": '''public class Solution {
    public boolean canFinish(int numCourses, int[][] prerequisites) {
        // Type your code here
        return true;
    }

    public static void main(String[] args) {
        Solution sol = new Solution();
        System.out.println("Can finish: " + sol.canFinish(2, new int[][]{{1, 0}}));
    }
}
''',
        "cpp": '''#include <iostream>
#include <vector>

class Solution {
public:
    bool canFinish(int numCourses, std::vector<std::vector<int>>& prerequisites) {
        // Type your code here
        return true;
    }
};

int main() {
    Solution sol;
    std::vector<std::vector<int>> prereqs = {{1, 0}};
    std::cout << "Can finish: " << sol.canFinish(2, prereqs) << std::endl;
    return 0;
}
''',
        "go": '''package main

import "fmt"

func canFinish(numCourses int, prerequisites [][]int) bool {
    // Type your code here
    return true
}

func main() {
    prereqs := [][]int{{1, 0}}
    fmt.Println("Can finish:", canFinish(2, prereqs))
}
'''
    },

    # -------------------------------------------------------------
    # dp-1: Coin Change
    # -------------------------------------------------------------
    "dp-1": {
        "python": '''class Solution:
    def coinChange(self, coins: list[int], amount: int) -> int:
        # Type your code here
        pass

if __name__ == "__main__":
    sol = Solution()
    print("Min coins:", sol.coinChange([1, 2, 5], 11))
''',
        "javascript": '''function coinChange(coins, amount) {
  // Type your code here
  return -1;
}

console.log("Min coins:", coinChange([1, 2, 5], 11));
''',
        "java": '''public class Solution {
    public int coinChange(int[] coins, int amount) {
        // Type your code here
        return -1;
    }

    public static void main(String[] args) {
        Solution sol = new Solution();
        System.out.println("Min coins: " + sol.coinChange(new int[]{1, 2, 5}, 11));
    }
}
''',
        "cpp": '''#include <iostream>
#include <vector>

class Solution {
public:
    int coinChange(std::vector<int>& coins, int amount) {
        // Type your code here
        return -1;
    }
};

int main() {
    Solution sol;
    std::vector<int> coins = {1, 2, 5};
    std::cout << "Min coins: " << sol.coinChange(coins, 11) << std::endl;
    return 0;
}
''',
        "go": '''package main

import "fmt"

func coinChange(coins []int, amount int) int {
    // Type your code here
    return -1
}

func main() {
    fmt.Println("Min coins:", coinChange([]int{1, 2, 5}, 11))
}
'''
    }
}

class BoilerplateService:
    """Service to supply runnable code boilerplates for interview sessions."""

    def normalize_language(self, lang: str) -> str:
        """Normalize language identifier to one of our standard keys."""
        l = (lang or "python").lower().strip()
        if "js" in l or "javascript" in l or "node" in l:
            return "javascript"
        if "java" in l and "script" not in l:
            return "java"
        if "c++" in l or "cpp" in l:
            return "cpp"
        if "go" in l or "golang" in l:
            return "go"
        if "ts" in l or "typescript" in l:
            return "javascript"
        return "python"

    def get_intro_placeholder(self, language: str = "python") -> str:
        """Initial starter state before any technical problem is presented."""
        lang = self.normalize_language(language)
        if lang == "python":
            return "# When a technical problem is presented, your starter code will appear here.\n# Type your code here\n"
        elif lang == "javascript":
            return "// When a technical problem is presented, your starter code will appear here.\n// Type your code here\n"
        elif lang == "java":
            return "// When a technical problem is presented, your starter code will appear here.\n// Type your code here\n"
        elif lang == "cpp":
            return "// When a technical problem is presented, your starter code will appear here.\n// Type your code here\n"
        elif lang == "go":
            return "// When a technical problem is presented, your starter code will appear here.\n// Type your code here\n"
        return "# Type your code here\n"

    def get_boilerplate(
        self,
        question_id: Optional[str] = None,
        language: str = "python",
        topic: Optional[str] = None,
        question_item: Optional[QuestionItem] = None
    ) -> str:
        """Retrieve runnable boilerplate starter code for the specified question and language."""
        lang_key = self.normalize_language(language)

        # 1. Match by question ID
        qid = (question_id or (question_item.id if question_item else "")).strip().lower()
        if qid in BOILERPLATES and lang_key in BOILERPLATES[qid]:
            return BOILERPLATES[qid][lang_key]

        # 2. Dynamic template tailored to the asked question
        category = (question_item.category if question_item else (topic or "General Algorithm")).strip()
        problem_title = question_item.text.split("\n")[0] if question_item else f"Solve algorithmic problem on {category}"

        return self._generate_generic_template(category, problem_title, lang_key)

    def _generate_generic_template(self, category: str, problem_title: str, lang: str) -> str:
        """Generate structured starter code with only 'Type your code here'."""
        if lang == "python":
            return '''class Solution:
    def solve(self, data):
        # Type your code here
        pass

if __name__ == "__main__":
    sol = Solution()
    print("Result:", sol.solve([1, 2, 3]))
'''
        elif lang == "javascript":
            return '''function solve(data) {
  // Type your code here
}

console.log("Result:", solve([1, 2, 3]));
'''
        elif lang == "java":
            return '''import java.util.*;

public class Solution {
    public Object solve(int[] data) {
        // Type your code here
        return null;
    }

    public static void main(String[] args) {
        Solution sol = new Solution();
        System.out.println("Result: " + sol.solve(new int[]{1, 2, 3}));
    }
}
'''
        elif lang == "cpp":
            return '''#include <iostream>
#include <vector>

class Solution {
public:
    void solve(std::vector<int>& data) {
        // Type your code here
    }
};

int main() {
    Solution sol;
    std::vector<int> test = {1, 2, 3};
    sol.solve(test);
    std::cout << "Completed execution." << std::endl;
    return 0;
}
'''
        elif lang == "go":
            return '''package main

import "fmt"

func solve(data []int) interface{} {
    // Type your code here
    return nil
}

func main() {
    test := []int{1, 2, 3}
    fmt.Println("Result:", solve(test))
}
'''
        return '''class Solution:
    def solve(self, data):
        # Type your code here
        pass
'''

boilerplate_service = BoilerplateService()
