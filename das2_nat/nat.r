library(ggplot2)
library(reshape)
library(stringr)

r <- read.table("request.data", header=TRUE, row.names=1)
s <- read.table("success.data", header=TRUE, row.names=1)
sr <- s/r

r$nattype <- str_sub(rownames(r), -1)
sr$nattype <- str_sub(rownames(r), -1)

r$from <- str_sub(rownames(r), 0, -3)
sr$from <- str_sub(rownames(r), 0, -3)

rm <- melt(r, id.vars = c("from", "nattype"))
srm <- melt(sr, id.vars = c("from", "nattype"))

colnames(rm) <- c('from', 'nattype', 'to', 'requests')
colnames(srm) <- c('from', 'nattype', 'to', 'successrate')

d <- merge(rm, srm, sort=FALSE)
d <- na.omit(d)

d$to <- str_sub(d$to, 0, -3)

nattypes <- list('1'="Symmetric", '2'="Port Res", '3'="Restricted", '4'="Full Cone", '5'="Open", '6' = "Unknown", '9'="?")
mf_labeller <- function(var, value){
    value <- as.character(value)
    return(nattypes[value])
}

p <- ggplot(d, aes(x=to, y=from)) + theme_bw()
p <- p + facet_grid(nattype ~ ., scales = "free_y", labeller=mf_labeller)
p <- p + geom_point(aes(size=requests, color=successrate))
p <- p + scale_color_gradient2(low='red',mid="yellow", high="darkgreen", midpoint = 0.5)
p <- p + labs(x = "Node Receiving", y = "Node Requesting\n")
p <- p + opts(axis.text.x = theme_text(hjust=0, angle = -45))
p

ggsave(file="nat.png", width=8, height=6, dpi=100)