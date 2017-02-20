is.installed <- function(mypkg) is.element(mypkg, installed.packages()[,1])

toInstall <- c("ggplot2", "reshape", "stringr", "plyr", "foreach", "data.table", "igraph")
for (package in toInstall){
	if (is.installed(package) == FALSE){
		install.packages(package, repos = "http://cran.r-project.org")
	}
}
