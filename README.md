# Git-topological-commit-history
Topologically view the commit history of a local Git repository.

The commits are printed from youngest to oldest.

If the next commit to be printed is not the parent of the current commit, a "sticky end" is inserted into the output, followed by an empty line before printing the next commit. The "sticky end" contains the commit hashes of the parents of the current commit, with a "=" sign appended to the last hash.

On the other hand, if an empty line has just been printed, before printing the next commit hash H, print a "sticky start" line that starts with a "=" sign, and then the hashes of the children of H.

These "sticky starts" and "sticky ends" help us visualise how fragments are linked together - especially when there are branches.

As an example, the commit graph of:

![Example Commit Graph](https://user-images.githubusercontent.com/56947176/108521328-94e58580-7306-11eb-84ee-750a85f59571.png)

will be topologically printed as (assuming the outputs are the commits' respective hashes):

```
c5 branch-3
c4 branch-2 branch-5
c3
c1=

=
h2 branch-1
h1
h0
```
