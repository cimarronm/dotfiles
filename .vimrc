" Enable mouse
set mouse=a

" File syntax and completions
syntax on
filetype indent plugin on

set wildmode=list:longest
set completeopt=menu,longest,preview

set autoread

set ruler

set hlsearch
set incsearch
set smartcase

set tabstop=4
set softtabstop=4
set sw=4
set expandtab

" Always show statusbar
set laststatus=2

" Change to white on black colors
highlight Normal ctermfg=white ctermbg=black
set background=dark

" Set column marker for column 80
set colorcolumn=80
highlight ColorColumn ctermbg=grey

" Findall on current word
map <Leader>* :execute "vimgrep /\\<" . expand("<cword>") . "\\>/g **" <bar> cw <cr>

" Window movement
map <c-j> <c-w>j
map <c-k> <c-w>k
map <c-l> <c-w>l
map <c-h> <c-w>h

" Automatically tag line-ending whitespace
highlight ExtraWhitespace ctermbg=red guibg=red
autocmd InsertLeave * match ExtraWhitespace /\s\+$/

" Taglist options
let Tlist_Auto_Open = 1
let Tlist_Exit_OnlyWindow = 1
