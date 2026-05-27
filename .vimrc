" Plugins
call plug#begin()
Plug 'junegunn/fzf'
Plug 'junegunn/fzf.vim'
Plug 'vim-airline/vim-airline'
Plug 'ervandew/supertab'
Plug 'preservim/nerdtree'
Plug 'dense-analysis/ale'
Plug 'junegunn/vim-easy-align'
Plug 'github/copilot.vim'
call plug#end()

" Set Leader
let mapleader=" "

" Enable mouse
set mouse=a

" File syntax and completions
syntax on
filetype indent plugin on

" Autocompletion options
set wildmode=list:longest
set completeopt=menu,longest,preview

" Automatically read files updated outside the editor
set autoread

" Turn on ruler
set ruler

" Search options
set hlsearch
set incsearch
set smartcase

" Indent spacing
set tabstop=4
set softtabstop=4
set sw=4
set expandtab

" Always show statusbar
set laststatus=2

" Change colors
set background=dark
colorscheme torte

" Set column marker for column 90
set colorcolumn=90

" Findall on current word
map <leader>* :execute "vimgrep /\\<" . expand("<cword>") . "\\>/g **" <bar> cw <cr>

" Window movement
map <c-j> <c-w>j
map <c-k> <c-w>k
map <c-l> <c-w>l
map <c-h> <c-w>h

" Automatically tag line-ending whitespace
highlight ExtraWhitespace ctermbg=red guibg=red
autocmd InsertLeave,BufRead * match ExtraWhitespace /\s\+$/

" Numbering lines
set number
set relativenumber

" Scroll offset
set scrolloff=5

" Taglist options
let Tlist_Auto_Open = 1
let Tlist_Exit_OnlyWindow = 1

" Powerline
set rtp+=/Library/Frameworks/Python.framework/Versions/3.4/lib/python3.4/site-packages/powerline/bindings/vim

" Quickly edit vimrc
nnoremap ,v :edit   $MYVIMRC<CR>
nnoremap ,u :source $MYVIMRC<CR>

" EasyAlign
xnoremap <leader>a <Plug>(EasyAlign)
nnoremap <leader>a <Plug>(EasyAlign)

" Explore
cnoremap Ex NERDTreeFind

" FZF
nnoremap <leader>f :Files<cr>
