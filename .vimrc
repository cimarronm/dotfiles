" Leader
let mapleader=" "

" Plugins
call plug#begin()
Plug 'dense-analysis/ale'
Plug 'ervandew/supertab'
Plug 'github/copilot.vim'
Plug 'junegunn/fzf'
Plug 'junegunn/fzf.vim'
Plug 'junegunn/vim-easy-align'
Plug 'preservim/nerdtree'
Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-surround'
Plug 'vim-airline/vim-airline'
call plug#end()

" Core behavior
syntax on
filetype indent plugin on
set autoread
set hidden
set mouse=a
set updatetime=300

" Completion
set completeopt=menu,longest,preview
set wildmode=list:longest

" Search
set hlsearch
set incsearch
set ignorecase
set smartcase

" Editing
set tabstop=4
set softtabstop=4
set shiftwidth=4
set expandtab
set colorcolumn=100

" UI
set background=dark
colorscheme torte
set ruler
set laststatus=2
set number
set relativenumber
set scrolloff=5

" Clipboard
set clipboard=unnamedplus

" Whitespace highlighting
highlight ExtraWhitespace ctermbg=red guibg=red
autocmd InsertLeave,BufRead * match ExtraWhitespace /\s\+$/

" General mappings
nnoremap <leader>* :Rg <C-r><C-w><CR>
map <c-j> <c-w>j
map <c-k> <c-w>k
map <c-l> <c-w>l
map <c-h> <c-w>h

" Vimrc mappings
nnoremap ,v :edit   $MYVIMRC<CR>
nnoremap ,t :source $MYVIMRC \| PlugInstall<CR>
nnoremap ,u :source $MYVIMRC<CR>

" EasyAlign mappings
xnoremap <leader>a <Plug>(EasyAlign)
nnoremap <leader>a <Plug>(EasyAlign)

" NERDTree mappings
cnoremap Ex NERDTreeFind
nnoremap <leader>nf :NERDTreeFind<CR>

" Fugitive mappings
nnoremap <leader>gs :Git<CR>
nnoremap <leader>gd :Gvdiffsplit<CR>
nnoremap <leader>gb :Git blame<CR>
nnoremap <leader>gc :Git commit<CR>
nnoremap <leader>gl :Git log<CR>

" FZF mappings
nnoremap <leader>f :Files<CR>
nnoremap <leader>r :Rg<CR>
