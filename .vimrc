set mouse=a
syntax on
filetype indent plugin on
set hlsearch
set ruler
set incsearch
set tabstop=4
set softtabstop=4
set sw=4
set expandtab
set smartcase
"set number
set laststatus=2
set colorcolumn=80
highlight Normal ctermfg=white ctermbg=black
set background=dark
highlight ColorColumn ctermbg=white
let Tlist_Auto_Open = 1
map <Leader>* :execute "vimgrep /\\<" . expand("<cword>") . "\\>/g **" <bar> cw <cr>
