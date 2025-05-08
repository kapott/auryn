# Auryn

A small DSL to chain together tools into a toolchain. Made for my own personal amusement, by sparring with- and wrangling into submission- ChatGPT.
It actually did pretty well - as long as your own thoughts are clear, and you can express them clearly, it will be helpful.

Notes:
- Make sure that every parser name exists in the parsers/ directory. 
- Make sure all parsers are chmod +x'ed.
- Make sure you have all tools you call in your $PATH, or configure them nicely
- This DSL was created for making a toolchain - as such it's entirely encouraged to
    - Create one DSL per customer / client / starting point
    - Absolutely blow up the code

Usage:
`python3 auryn.py mock.dsl`

Todo:
- [ ] build or find reliable RR (Reverse DNS lookup for ip->hostname mappings)