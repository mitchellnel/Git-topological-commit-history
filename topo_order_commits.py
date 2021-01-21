"""
Create a directed, acyclic graph of commits, and sort that graph using a
 topological ordering.
"""

import os, sys, zlib


# CommitNode class for helping build our commit graph
class CommitNode:
    """
    A class used to represent a commit object in a Git repository

    Attributes
    ----------
    commit_hash : str
        the hash value of the commit object
    parents : set
        a set of the commit objects parent commits
    children : set
        a set of the commit objects children commits
    """

    def __init__(self, commit_hash):
        """
        :type commit_hash: str
        """
        self.commit_hash = commit_hash
        self.parents = set()
        self.children = set()

    # two CommitNodes are equal if they have the same commit_hash
    def __eq__(self, other):
        return self.commit_hash == other.commit_hash

    # string cast for debugging
    def __str__(self):
        return "Hash: " + self.commit_hash + "\nParents: " + str(self.parents) + "\nChildren: " + str(self.children) \
               + '\n'


# Titular function
def topo_order_commits():
    """Topologically order the commits in a Git repository, and print them out"""
    # Step 1: Find the .git directory
    git_dir = find_git_dir()

    # Step 2: Get the list of local branch names
    branches = find_branches(git_dir)
    branch_head_hashes = list(branches.keys())

    # Step 3: Build the commit graph
    commit_nodes, root_nodes = build_commit_graph(git_dir, branch_head_hashes)
    root_hashes = list(root_nodes.keys())

    # Step 4: Topologically sort the commit objects
    topo_ordered_hashes = get_topo_ordered_commits(commit_nodes, root_hashes)

    # Step 5: Print the sorted order
    print_topo_ordered_commits_with_branch_names(commit_nodes, topo_ordered_hashes, branches)


# Step 1 function
def find_git_dir():
    """Find the .git directory from the calling location

    :returns a path to the .git directory from the script calling location
    """

    curr_dir = "."

    # until we reach the root directory
    while os.path.abspath(curr_dir) != '/':
        # look at all the directories in the curr_dir to see if .git exists
        dir_list = os.listdir(curr_dir)

        for d in dir_list:
            if d == ".git" and os.path.isdir(os.path.join(curr_dir, d)):
                # return the path of the .git folder, relative to script calling location
                git_path = os.path.join(curr_dir, ".git")
                return git_path

        # if we didn't find .git, move up to parent directory
        curr_dir = os.path.join("..", curr_dir)

    # if we reach here, we reached the root directory
    # so send an error message to stderr, and exit with status 1
    reached_root_err = "Not inside a Git repository"

    sys.stderr.write(reached_root_err)
    sys.exit(1)


# Step 2 function
def find_branches(git_dir):
    """Find all local branch names

    :param git_dir: the full path of the .git directory, relative to script calling location
    :type git_dir: str

    :returns dict with keys as head commit hashes, and values as branch names
    """
    branch_ref_path = os.path.join(git_dir, "refs/heads/")

    # key is branch name, value is commit hash
    branches = {}

    # list of subdirectories to look into
    sub_dir_list = [branch_ref_path]

    # until there are no more directories to explore
    while len(sub_dir_list) != 0:
        curr_dir = sub_dir_list.pop(0)

        # look at all the files in refs/heads/ to get names and hashes
        file_list = os.listdir(curr_dir)

        # add all of file_list to sub_dir_list, we'll remove the non-dirs later
        sub_dir_list.extend(file_list)

        for file in file_list:
            if os.path.isfile(os.path.join(curr_dir, file)):
                full_branch_path = os.path.join(curr_dir, file)

                # get name of branch for dict value
                branch_name = isolate_branch_name(full_branch_path)

                # open the file containing the ref and read it
                file_obj = open(os.path.join(curr_dir, file), 'r')
                hash = file_obj.read().strip('\n')
                file_obj.close()

                # add branch_name to dict under associated hash
                if hash not in branches:
                    branches[hash] = list()

                branches[hash].append(branch_name)

                # remove non-dir from sub_dir_list
                sub_dir_list.remove(file)

        # after this for loop, the only elements in sub_dir_list are other directories

        # get a path for each of the sub-dirs
        for i in range(len(sub_dir_list)):
            sub_dir = os.path.join(curr_dir, sub_dir_list[i])
            sub_dir_list[i] = sub_dir

    return branches


# Step 2 helper function
def isolate_branch_name(full_branch_path):
    """Isolate the true branch name for a Git branch

    :param full_branch_path: the full path to the branch head ref, relative to script calling location
    :type full_branch_path: str

    :returns the true branch name for a Git branch
    """

    # split the path into its "elems" == individual directories
    path_elems = full_branch_path.split("/")

    # get rid of the ......./.git/refs/heads/
    for i in range(len(path_elems)):
        if path_elems[i] == "heads":
            branch_name_elems = path_elems[i+1:len(path_elems)]
            break

    branch_name = "/".join(branch_name_elems)

    return branch_name


# Step 3 function
def build_commit_graph(git_path, local_branch_heads):
    """Build the full commit graph by using the local branch head hashes

    :param git_path: the full path of the .git directory, relative to script calling location
    :type git_path: str

    :param  local_branch_heads: commit hashes for each of the local branch heads
    :type local_branch_heads: list

    :returns a dict of commit_nodes and root_nodes - in both, key is the commit hash, and value is the CommitNode object
    """
    commit_nodes = dict()   # keys are hashes, values are CommitNodes
    root_nodes = dict()      # keys are root node hashes, values are root CommitNodes
    visited = set()         # keep track of already looked at commit hashes for DFS

    stack = local_branch_heads
    while stack:
        # Get the next element from stack, store it in commit_hash, and remove it from stack
        commit_hash = local_branch_heads.pop()

        if commit_hash in visited:
            # What do you do if the commit we’re on is already in visited?
            continue

        visited.add(commit_hash)

        if commit_hash not in commit_nodes:
            # What do you do if the commit we’re on isn’t in commit_nodes?
            commit_nodes[commit_hash] = CommitNode(commit_hash)

        curr_commit_node = commit_nodes[commit_hash]

        # Find commit_hash in the objects folder, decompress it, and get parent commits
        curr_commit_node.parents = find_commit_node_parents(git_path, curr_commit_node)

        if not curr_commit_node.parents:
            # What list do we add commit_hash to if it doesn’t have any parent commits?
            root_nodes[commit_hash] = curr_commit_node

        for parent_hash in curr_commit_node.parents:
            if parent_hash not in visited:
                # What do we do if p isn’t in visited?
                local_branch_heads.append(parent_hash)

            if parent_hash not in commit_nodes:
                # What do we do if p isn’t in commit_nodes?
                commit_nodes[parent_hash] = CommitNode(parent_hash)

            p_curr_commit_node = commit_nodes[parent_hash]

            # how do we record that commit_hash is a child of commit node p?
            p_curr_commit_node.children.add(commit_hash)

    return commit_nodes, root_nodes


# Step 3 helper function
def find_commit_node_parents(git_path, commit_node):
    """Finds parents of a commit node

    :param git_path: the full path of the .git directory, relative to script calling location
    :type git_path: str

    :param commit_node: the commit_node to find the parents for
    :type commit_node: CommitNode

    :returns a list of the commit hashes for commit_node's parents
    """
    commit_obj_path = os.path.join(git_path, "objects/")

    commit_hash = commit_node.commit_hash

    parent_hashes = set()

    # commit obj path will be in the directory of the first 2 characters of the hash
    commit_obj_path = os.path.join(commit_obj_path, commit_hash[0] + commit_hash[1])

    # remove the first two characters from the filename hash
    for i in range(0, 2):
        commit_hash = list(commit_hash)
        commit_hash[0] = ''
        commit_hash = "".join(commit_hash)

    # full path for the actual commit object
    commit_obj_path = os.path.join(commit_obj_path, commit_hash)

    # decompress and decode
    compressed_contents = open(commit_obj_path, 'rb').read()
    decompressed_contents = zlib.decompress(compressed_contents)
    decoded_contents = decompressed_contents.decode("utf-8")

    # extract parent hashes
    decompressed_contents_by_element = decoded_contents.splitlines()

    for element in decompressed_contents_by_element:
        if "parent" in element:
            # extract hash and append to set
            parent_hashes.add(element.split(' ')[1])

    return parent_hashes


# Step 4 function
def get_topo_ordered_commits(commit_nodes, root_hashes):
    """Topologically sort commit nodes

    :param commit_nodes: a dict of the CommitNode objects, keyed by their hashes
    :type commit_nodes: dict

    :param root_hashes: a list of the hashes for the root commit nodes
    :type root_hashes: list

    :returns a list of the correct topological ordering of commit hashes
    """
    order = []
    visited = set()

    temp_stack = []
    stack = sorted(root_hashes)

    while stack:
        v = stack.pop()

        if v in visited:
            # what do you do if v is already visited?
            continue

        visited.add(v)

        if temp_stack:
            top_hash = temp_stack[-1]

        # get children of popped vertex
        while len(temp_stack) != 0 and v not in commit_nodes[top_hash].children:
            g = temp_stack.pop()
            order.append(g)

            top_hash = temp_stack[-1]

        temp_stack.append(v)

        for c in sorted(commit_nodes[v].children):
            # What do you do is c has already been visited?
            if c not in visited:
                stack.append(c)

    # Add the rest of the temp_stack to the order
    temp_stack.reverse()

    for hash in temp_stack:
        order.append(hash)

    return order


# Step 5 function
def print_topo_ordered_commits_with_branch_names(commit_nodes, topo_ordered_commits, head_to_branches):
    """Print the topologically ordered commits in the style of the spec

    :param commit_nodes: a dict of the CommitNode objects, keyed by their hashes
    :type commit_nodes: dict

    :param topo_ordered_commits: a list of commit hashes, topologically sorted
    :type topo_ordered_commits: list

    :param head_to_branches: a dict of the local branches, keys are the head hashes, values are the branch names
    :type head_to_branches: dict
    """

    # sort parents and children of commit_nodes to address determinism case
    # by doing this, parents and children will be ordered the same for any call of this script
    for node in commit_nodes:
        commit_nodes[node].parents = sorted(commit_nodes[node].parents)
        commit_nodes[node].children = sorted(commit_nodes[node].children)

    jumped = False

    for i in range(len(topo_ordered_commits)):
        commit_hash = topo_ordered_commits[i]

        if jumped:
            jumped = False

            sticky_hash = ' '.join(commit_nodes[commit_hash].children)
            print(f'={sticky_hash}')

        branches = sorted(head_to_branches[commit_hash]) if commit_hash in head_to_branches else []

        print(commit_hash + (' ' + ' '.join(branches) if branches else ''))

        if i+1 < len(topo_ordered_commits) and topo_ordered_commits[i+1] not in commit_nodes[commit_hash].parents:
            jumped = True

            sticky_hash = ' '.join(commit_nodes[commit_hash].parents)
            print(f'{sticky_hash}=\n')


# main call
if __name__ == "__main__":
    topo_order_commits()
