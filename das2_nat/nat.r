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
midpoint <- 0.5
d$to <- str_sub(d$to, 0, -3)

p <- ggplot(d, aes(x=to, y=from)) + theme_bw()
p <- p + facet_grid(nattype ~ ., scales = "free_y")
p <- p + geom_point(aes(size=requests, color=successrate))
p <- p + scale_color_gradient2(low='red',mid="yellow", high="darkgreen", midpoint = midpoint)
p <- p + labs(x = "Node Receiving", y = "Node Requesting\n") + opts(axis.text.x = theme_text(hjust = 0, colour = "grey50", angle = -45), axis.text.y = theme_text(colour = "grey50"))
p

ggsave(file="nat.png", width=8, height=6, dpi=100)